# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "substrate-interface>=1.7.0",
#     "rich>=13.0.0",
#     "websocket-client>=1.6.0",
# ]
# ///
from typing import Optional, Dict, Any, Tuple
from substrateinterface import SubstrateInterface, Keypair, ExtrinsicReceipt
from rich.console import Console
from rich.progress import Progress
from pathlib import Path
import json
import sys
import time
import signal
import inspect
import argparse
from dataclasses import dataclass

# Configuration
@dataclass
class Config:
    node_url: str = "wss://testnet.api.communeai.net"
    timeout: int = 300  # 5 minutes in seconds
    era_period: int = 64  # blocks
    key_dir: Path = Path.home() / ".commune" / "key"

# Helper function to get the current line number
def get_lineno() -> int:
    """Get the current line number for debugging purposes."""
    return inspect.currentframe().f_back.f_lineno

# Initialize console for rich output
console = Console()

class TimeoutError(Exception):
    """Exception raised when an operation times out."""
    pass

def timeout_handler(signum: int, frame: Any) -> None:
    """Handle operation timeout by raising TimeoutError."""
    raise TimeoutError("Operation timed out")

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Submit a runtime upgrade to the Substrate node.")
    parser.add_argument(
        "--node-url", 
        default=Config.node_url,
        help=f"Node URL (default: {Config.node_url})"
    )
    parser.add_argument(
        "--key", 
        required=True,
        help="Name of the sudo key to use (without .json extension)"
    )
    parser.add_argument(
        "--wasm-path",
        required=True,
        help="Path to the compiled WASM runtime"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=Config.timeout,
        help=f"Operation timeout in seconds (default: {Config.timeout})"
    )
    return parser.parse_args()

def load_sudo_key(key_name: str, key_dir: Path) -> Optional[Keypair]:
    """Load a keypair from the specified directory.
    
    Args:
        key_name: Name of the key (without .json extension)
        key_dir: Directory containing the key files
        
    Returns:
        Keypair if successful, None otherwise
    """
    try:
        key_path = key_dir / f"{key_name}.json"
        
        if not key_path.exists():
            console.print(f"[red]✗ Key {key_name} not found in {key_dir}[/red]")
            return None
        
        key_data = json.loads(key_path.read_text())["data"]
        key_dict = json.loads(key_data)
        keypair = Keypair(
            ss58_address=key_dict["ss58_address"],
            private_key=key_dict["private_key"],
            public_key=key_dict["public_key"]
        )
        console.print(f"[green]✓ Loaded sudo key {key_name}[/green]")
        return keypair
        
    except Exception as e:
        console.print(f"[red]✗ Error loading key {key_name}: {e}[/red]")
        if hasattr(e, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
        return None

def connect_to_runtime(node_url: str) -> Optional[SubstrateInterface]:
    """Connect to the Substrate node.
    
    Args:
        node_url: URL of the node to connect to
        
    Returns:
        SubstrateInterface instance if successful, None otherwise
    """
    try:
        console.print(f"\n[blue]Connecting to node at {node_url}...[/blue]")
        substrate = SubstrateInterface(
            url=node_url,
            ss58_format=42,
            type_registry_preset='substrate-node-template',
            use_remote_preset=True,
            ws_options={
                'ping_interval': 30,
                'ping_timeout': 10,
                'close_timeout': 10,
            },
            auto_discover=True,
            auto_reconnect=True,
        )
        console.print("[green]✓ Connected to node[/green]")
        return substrate
    except Exception as e:
        console.print(f"[red]✗ Error connecting to node: {e}[/red]")
        if hasattr(e, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
        return None

def get_account_info(substrate: SubstrateInterface, sudo_key: Keypair) -> Optional[Any]:
    """Fetch account information from the chain.
    
    Args:
        substrate: Connected Substrate interface
        sudo_key: Keypair to get info for
        
    Returns:
        Account info object if successful, None otherwise
    """
    try:
        console.print("\n[blue]Fetching account info...[/blue]")
        account_info = substrate.query(
            module='System',
            storage_function='Account',
            params=[sudo_key.ss58_address]
        )
        
        if not account_info:
            console.print("[red]✗ Account not found on chain[/red]")
            return None
            
        console.print("[green]✓ Account info retrieved[/green]")
        return account_info

    except Exception as e:
        console.print(f"[red]✗ Error fetching account info: {e}")
        if hasattr(e, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
        return None

def check_account_balance(account_info: Any, min_balance: float = 15.0) -> bool:
    """Check if the account has sufficient balance.
    
    Args:
        account_info: Account information object from Substrate
        min_balance: Minimum required balance in tokens
        
    Returns:
        True if balance is sufficient, False otherwise
    """
    try:
        console.print("\n[blue]Checking account balance...[/blue]")
        
        # Debug print the raw account info
        console.print(f"[yellow]Raw account info: {account_info}[/yellow]")
        
        # Get the raw account data as a dictionary
        if hasattr(account_info, 'to_dict'):
            account_dict = account_info.to_dict()
        elif hasattr(account_info, 'serialize'):
            account_dict = account_info.serialize()
        else:
            account_dict = dict(account_info)
            
        console.print(f"[yellow]Account dict: {account_dict}[/yellow]")
        
        # Extract the free balance
        if 'data' in account_dict and 'free' in account_dict['data']:
            free_balance = account_dict['data']['free']
        elif 'value' in account_dict and 'data' in account_dict['value'] and 'free' in account_dict['value']['data']:
            free_balance = account_dict['value']['data']['free']
        else:
            console.print("[red]✗ Could not find free balance in account data[/red]")
            return False
            
        # Convert to integer if it's a ScaleBytes object or a string
        if hasattr(free_balance, 'value'):
            free_balance = int(free_balance.value)
        elif isinstance(free_balance, str) and free_balance.startswith('0x'):
            # Handle hex string
            free_balance = int(free_balance, 16)
        else:
            free_balance = int(free_balance)
        
        # Convert to tokens (assuming 9 decimal places)
        free_balance_tokens = free_balance / 1e9
        console.print(f"[green]✓ Free balance: {free_balance_tokens:,.2f} tokens[/green]")
        
        if free_balance_tokens < min_balance:
            console.print(f"[red]✗ Insufficient balance. Need at least {min_balance} tokens for the operation.[/red]")
            return False
            
        return True

    except Exception as e:
        console.print(f"[red]✗ Error checking account balance: {e}")
        if hasattr(e, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
        return False
            
def get_wasm_blob(wasm_path: str) -> Optional[bytes]:
    """Read and return the WASM runtime blob.
    
    Args:
        wasm_path: Path to the WASM file
        
    Returns:
        Bytes of the WASM blob if successful, None otherwise
    """
    try:
        wasm_path_obj = Path(wasm_path).expanduser().resolve()
        console.print(f"[blue]Reading WASM file from: {wasm_path_obj}[/blue]")
        
        with open(wasm_path_obj, 'rb') as f:
            wasm_blob = f.read()
            
        size_mb = len(wasm_blob) / (1024 * 1024)
        console.print(f"[green]✓ Read WASM blob: {size_mb:.2f} MB[/green]")
        return wasm_blob
        
    except FileNotFoundError:
        console.print(f"[red]✗ WASM file not found: {wasm_path_obj}[/red]")
        return None
        
    except Exception as e:
        console.print(f"[red]✗ Error reading WASM file: {e}")
        if hasattr(e, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
        return None

def create_runtime_upgrade_call(substrate: SubstrateInterface, wasm_blob: bytes) -> Optional[Any]:
    """Create a runtime upgrade call wrapped in a sudo call.
    
    Args:
        substrate: Connected Substrate interface
        wasm_blob: Compiled WASM runtime as bytes
        
    Returns:
        Composed call if successful, None otherwise
    """
    try:
        # First, create the set_code call
        set_code_call = substrate.compose_call(
            call_module='System',
            call_function='set_code',
            call_params={
                'code': '0x' + wasm_blob.hex()
            }
        )
        
        # Then wrap it in a sudo call
        sudo_call = substrate.compose_call(
            call_module='Sudo',
            call_function='sudo',
            call_params={
                'call': set_code_call
            }
        )
        
        return sudo_call
        
    except Exception as e:
        console.print(f"[red]✗ Error creating runtime upgrade call: {e}")
        if hasattr(e, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
        return None

def get_block_number(substrate: SubstrateInterface) -> Optional[int]:
    """Get the current block number.
    
    Args:
        substrate: Connected Substrate interface
        
    Returns:
        Current block number if successful, None otherwise
    """
    try:
        current_block = substrate.get_block_header()
        block_number = current_block['header']['number']
        console.print(f"[blue]Current block: {block_number}[/blue]")
        return block_number
        
    except Exception as e:
        console.print(f"[red]✗ Error getting block number: {e}")
        if hasattr(e, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
        return None

def construct_extrinsic(
    substrate: SubstrateInterface,
    call: Any,
    block_number: int,
    sudo_key: Keypair,
    account_info: Any,
    max_attempts: int = 3
) -> Optional[Any]:
    """Construct a signed extrinsic with retry logic.
    
    Args:
        substrate: Connected Substrate interface
        call: The call to include in the extrinsic
        block_number: Initial block number (will be refreshed)
        sudo_key: Keypair to sign the extrinsic
        account_info: Account info object from Substrate
        max_attempts: Maximum number of attempts to construct the extrinsic
        
    Returns:
        Constructed extrinsic if successful, None otherwise
    """
    attempt = 0
    last_error = None
    
    while attempt < max_attempts:
        try:
            # Get fresh account info to ensure we have the latest nonce
            account_info = substrate.query(
                module='System',
                storage_function='Account',
                params=[sudo_key.ss58_address]
            )
            
            # Debug log account info
            console.print(f"[debug] Account info type: {type(account_info)}")
            console.print(f"[debug] Account info: {account_info}")
            
            # Get a fresh block header
            block_header = substrate.get_block_header()
            console.print(f"[debug] Block header type: {type(block_header)}")
            console.print(f"[debug] Block header: {block_header}")
            
            # Extract block number safely
            current_block = block_header['header']['number']
            console.print(f"[debug] Block number type: {type(current_block)}")
            console.print(f"[debug] Block number: {current_block}")
            
            # Get the current nonce and convert to int if it's a U32 object
            nonce = account_info['nonce']
            console.print(f"[debug] Nonce type: {type(nonce)}")
            console.print(f"[debug] Nonce: {nonce}")
            
            # Convert nonce to int if it's a U32 object
            if hasattr(nonce, 'value'):
                nonce = int(nonce.value)
                console.print(f"[debug] Converted nonce to int: {nonce}")
            
            console.print(f"\n[blue]Attempt {attempt + 1}/{max_attempts}[/blue]")
            console.print(f"Using nonce: {nonce}")
            console.print(f"Using block number: {current_block} (refreshed)")
            
            # Create the extrinsic with sudo_unchecked_weight
            sudo_call = substrate.compose_call(
                call_module='Sudo',
                call_function='sudo_unchecked_weight',
                call_params={
                    'call': call,
                    'weight': {
                        'ref_time': 1000000000,  # Adjust weight as needed
                        'proof_size': 1024,
                    }
                }
            )
            
            # Create the signed extrinsic with a short era period
            extrinsic = substrate.create_signed_extrinsic(
                call=sudo_call,
                keypair=sudo_key,
                era={'period': 32},  # Shorter era period (32 blocks ~ 5 minutes)
                nonce=nonce,
                tip=0,
            )
            
            # Verify the extrinsic is valid
            if not extrinsic:
                raise ValueError("Failed to create signed extrinsic")
                
            console.print("[green]✓ Extrinsic constructed successfully[/green]")
            return extrinsic
            
        except Exception as e:
            last_error = e
            attempt += 1
            wait_time = 2 ** attempt  # Exponential backoff
            
            console.print(f"[yellow]⚠ Attempt {attempt}/{max_attempts} failed: {e}[/yellow]")
            if attempt < max_attempts:
                console.print(f"[yellow]Retrying in {wait_time} seconds...[/yellow]")
                time.sleep(wait_time)
    
    # If we get here, all attempts failed
    console.print(f"[red]✗ Failed to construct extrinsic after {max_attempts} attempts[/red]")
    if last_error:
        console.print(f"[red]Last error: {last_error}[/red]")
        if hasattr(last_error, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
    return None

def submit_extrinsic(
    substrate: SubstrateInterface,
    extrinsic: Any,
    timeout: int = Config.timeout,
    max_retries: int = 3
) -> Optional[ExtrinsicReceipt]:
    """Submit an extrinsic and wait for inclusion with retry logic.
    
    Args:
        substrate: Connected Substrate interface
        extrinsic: The extrinsic to submit
        timeout: Timeout in seconds for each attempt
        max_retries: Maximum number of retry attempts
        
    Returns:
        Extrinsic receipt if successful, None otherwise
    """
    attempt = 0
    last_error = None
    
    while attempt < max_retries:
        try:
            console.print(f"\n[blue]Submitting extrinsic (Attempt {attempt + 1}/{max_retries})...[/blue]")
            
            # Set up timeout handler
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout)
            
            try:
                # Submit the extrinsic and wait for inclusion
                result = substrate.submit_extrinsic(
                    extrinsic=extrinsic,
                    wait_for_inclusion=True,
                    wait_for_finalization=False
                )
                
                # Check if the extrinsic was included
                if result.is_success:
                    console.print("[green]✓ Extrinsic included in block[/green]")
                    
                    # Handle block hash (it might be a string or bytes)
                    block_hash = result.block_hash
                    if hasattr(block_hash, 'hex'):
                        block_hash = block_hash.hex()
                    console.print(f"Block hash: {block_hash}")
                    
                    # Show relevant events
                    if hasattr(result, 'triggered_events'):
                        console.print("\n[blue]Events:[/blue]")
                        for event in result.triggered_events:
                            try:
                                if hasattr(event, 'value') and 'event' in event.value:
                                    event_data = event.value['event']
                                    if 'module_id' in event_data and 'event_id' in event_data:
                                        console.print(f"- {event_data['module_id']}.{event_data['event_id']}")
                            except Exception as e:
                                console.print(f"[yellow]⚠ Could not parse event: {e}[/yellow]")
                    
                    return result
                else:
                    error_msg = getattr(result, 'error_message', 'Unknown error')
                    raise Exception(f"Extrinsic failed: {error_msg}")
                    
            except TimeoutError:
                raise TimeoutError("Operation timed out while waiting for extrinsic inclusion")
                
            except Exception as e:
                error_str = str(e)
                if "Transaction is outdated" in error_str or "Invalid Transaction" in error_str:
                    # This is a non-retryable error for the same extrinsic
                    raise Exception(f"Transaction is outdated or invalid: {e}")
                raise Exception(f"Error during extrinsic submission: {e}")
                
            finally:
                # Always reset the alarm
                signal.alarm(0)
                
        except Exception as e:
            last_error = e
            attempt += 1
            
            # Check if this is a temporary ban error
            error_str = str(e)
            if "temporarily banned" in error_str or "temporary bann" in error_str:
                # For temporary bans, wait longer before retrying
                wait_time = 30  # Wait 30 seconds for bans to clear
                console.print(f"[yellow]⚠ Temporary ban detected. Waiting {wait_time} seconds before retry...[/yellow]")
            else:
                # Use exponential backoff for other errors
                wait_time = 2 ** attempt
                
            console.print(f"[yellow]⚠ Attempt {attempt}/{max_retries} failed: {e}[/yellow]")
            
            if attempt < max_retries:
                console.print(f"[yellow]Retrying in {wait_time} seconds...[/yellow]")
                time.sleep(wait_time)
    
    # If we get here, all attempts failed
    console.print(f"[red]✗ Failed to submit extrinsic after {max_retries} attempts[/red]")
    if last_error:
        console.print(f"[red]Last error: {last_error}[/red]")
    return None

def submit_runtime_upgrade(
    wasm_path: str,
    key_name: str,
    node_url: str = Config.node_url,
    timeout: int = Config.timeout,
    era_period: int = Config.era_period
) -> bool:
    """Main function to submit a runtime upgrade.
    
    Args:
        wasm_path: Path to the compiled WASM runtime
        key_name: Name of the sudo key (without .json)
        node_url: URL of the Substrate node
        timeout: Timeout in seconds
        era_period: Number of blocks the transaction is valid for
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Connect to the node
        substrate = connect_to_runtime(node_url)
        if not substrate:
            return False
            
        # Load the sudo key
        sudo_key = load_sudo_key(key_name, Config.key_dir)
        if not sudo_key:
            return False
            
        console.print(f"Using account: {sudo_key.ss58_address}\n")
        
        # Get account info
        account_info = get_account_info(substrate, sudo_key)
        if not account_info:
            return False
            
        # Check account balance
        if not check_account_balance(account_info):
            return False
            
        # Read the WASM file
        wasm_blob = get_wasm_blob(wasm_path)
        if not wasm_blob:
            return False
            
        # Create the runtime upgrade call
        console.print("\n[blue]Creating runtime upgrade call...[/blue]")
        
        # Get current block number
        block_header = substrate.get_block_header()
        block_number = block_header['header']['number']
        console.print(f"Current block: {block_number}")
        
        # Create the call
        call = create_runtime_upgrade_call(substrate, wasm_blob)
        if not call:
            return False
            
        # Get a fresh block number right before creating the extrinsic
        block_header = substrate.get_block_header()
        fresh_block_number = block_header['header']['number']
        
        # Construct the extrinsic
        extrinsic = construct_extrinsic(
            substrate=substrate,
            call=call,
            block_number=fresh_block_number,
            sudo_key=sudo_key,
            account_info=account_info
        )
        
        if not extrinsic:
            return False
            
        # Submit the extrinsic
        receipt = submit_extrinsic(substrate, extrinsic, timeout)
        
        if receipt and receipt.is_success:
            console.print("\n[green]✓ Runtime upgrade submitted successfully![/green]")
            return True
        else:
            console.print("\n[red]✗ Failed to submit runtime upgrade[/red]")
            return False
            
    except Exception as e:
        console.print(f"\n[red]✗ Runtime upgrade process failed")
        if hasattr(e, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        # Ensure the alarm is always reset
        signal.alarm(0)

if __name__ == "__main__":
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Run the main function with command line arguments
        success = submit_runtime_upgrade(
            wasm_path=args.wasm_path,
            key_name=args.key,
            node_url=args.node_url,
            timeout=args.timeout
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]✗ Error: {e}[/red]")
        if hasattr(e, '__traceback__'):
            import traceback
            console.print(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
