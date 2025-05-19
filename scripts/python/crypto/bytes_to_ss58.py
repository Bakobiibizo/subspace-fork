# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "substrate-interface",
#     "rich",
# ]
# ///
"""
Convert a bytes array from a Rust file to an SS58 address.

Usage:
    python bytes_to_ss58.py <path_to_rust_file> [--array-name ARRAY_NAME]

Example:
    python bytes_to_ss58.py ../../runtime/src/precompiles/balance_transfer.rs --array-name SRC_ADDRESS
"""

import sys
import re
from pathlib import Path
from typing import Optional, Tuple, List
from substrateinterface import Keypair, KeypairType
from rich.console import Console

console = Console()


def extract_bytes_array(file_path: Path, array_name: str = "SRC_ADDRESS") -> Optional[bytes]:
    """Extract a bytes array from a Rust file."""
    try:
        content = file_path.read_text()
        
        # Look for patterns like: `const ARRAY_NAME: [u8; 32] = [ ... ]`
        pattern = re.compile(
            rf'const\s+{re.escape(array_name)}\s*:\s*\[u8;\s*\d+\]\s*=\s*\[(.*?)\]',
            re.DOTALL
        )
        
        match = pattern.search(content)
        if not match:
            print(f"Error: Could not find {array_name} array in {file_path}")
            return None
            
        # Extract and clean the array content
        array_content = match.group(1).strip()
        
        # Remove comments and split by commas
        bytes_list = []
        for item in array_content.split(','):
            item = item.split('//')[0].strip()  # Remove inline comments
            if not item:
                continue
                
            # Handle hex (0x) and decimal values
            if item.startswith('0x'):
                try:
                    bytes_list.append(int(item, 16))
                except ValueError:
                    print(f"Warning: Could not parse hex value: {item}")
            else:
                try:
                    bytes_list.append(int(item))
                except ValueError:
                    print(f"Warning: Could not parse value: {item}")
        
        return bytes(bytes_list)
        
    except Exception as e:
        print(f"Error extracting bytes array: {e}")
        return None


def bytes_to_ss58(public_key: bytes, ss58_format: int = 42) -> str:
    """
    Convert raw bytes to an SS58 address.
    
    Args:
        public_key: Raw public key bytes (32 bytes for SR25519)
        ss58_format: SS58 format number (42 for Subspace)
        
    Returns:
        SS58-encoded address string
    """
    try:
        if len(public_key) != 32:
            print(f"[yellow]Warning: Expected 32-byte public key, got {len(public_key)} bytes")
            if len(public_key) < 32:
                # Pad with zeros if too short
                public_key = public_key + bytes([0] * (32 - len(public_key)))
                print(f"[yellow]Padded to 32 bytes: {public_key.hex()}")
            else:
                # Truncate if too long
                public_key = public_key[:32]
                print(f"[yellow]Truncated to 32 bytes: {public_key.hex()}")
        
        # Create keypair with SR25519 crypto type (used by Subspace)
        keypair = Keypair(
            public_key=public_key,
            ss58_format=ss58_format,
            crypto_type=KeypairType.SR25519
        )
        return keypair.ss58_address
    except Exception as e:
        print(f"[red]Error converting to SS58: {e}")
        print(f"[red]Public key (hex): {public_key.hex() if public_key else 'None'}")
        print(f"[red]Length: {len(public_key) if public_key else 0} bytes")
        raise


def test_known_addresses() -> List[Tuple[bytes, str]]:
    """Test with known public key/address pairs."""
    # Format: (public_key_hex, expected_ss58)
    test_vectors = [
        # Alice's key (well-known Substrate dev account)
        (
            bytes.fromhex("d43593c715fdd31c61141abd04a99fd6822c8558854ccde39a5684e7a56da27d"),
            "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
        ),
        # Bob's key (well-known Substrate dev account)
        (
            bytes.fromhex("8eaf04151687736326c9fea17e25fc5287613693c912909cb226aa4794f26a48"),
            "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        ),
        # All zeros edge case
        (
            bytes(32),  # 32 zero bytes
            "5C4hrfjw9DjXZTzV3MwzrrAr9P1MJhSrvWGWqi1eSuyUpnhM"
        )
    ]
    
    console.print("\n[bold]Testing with known addresses:[/bold]")
    results = []
    for pubkey, expected_ss58 in test_vectors:
        try:
            ss58 = bytes_to_ss58(pubkey)
            match = ss58 == expected_ss58
            status = "[green]✓[/green]" if match else "[red]✗[/red]"
            results.append((pubkey.hex(), ss58, expected_ss58, match))
            console.print(f"{status} {pubkey.hex()[:8]}... -> {ss58}")
            if not match:
                console.print(f"   Expected: {expected_ss58}")
        except Exception as e:
            console.print(f"[red]✗ Error: {e}[/red]")
            results.append((pubkey.hex(), str(e), expected_ss58, False))
    
    return results

def main():
    if len(sys.argv) < 2:
        console.print("[red]Error: Please provide a Rust file path[/red]")
        console.print("\nUsage: python bytes_to_ss58.py <path_to_rust_file> [--array-name ARRAY_NAME]")
        sys.exit(1)
    
    # First run tests with known addresses
    test_results = test_known_addresses()
    if not all(r[3] for r in test_results):
        console.print("\n[red]Warning: Some test vectors failed. Proceeding with conversion, but results may be incorrect.[/red]")
    
    # Proceed with file parsing
    file_path = Path(sys.argv[1]).resolve()
    array_name = "SRC_ADDRESS"  # Default array name
    
    # Parse optional arguments
    if "--array-name" in sys.argv:
        try:
            idx = sys.argv.index("--array-name")
            array_name = sys.argv[idx + 1]
        except IndexError:
            console.print("[red]Error: --array-name requires a value[/red]")
            sys.exit(1)
    
    console.print(f"\n[bold]Looking for array '{array_name}' in {file_path}[/bold]")
    
    # Extract and convert the bytes
    public_key = extract_bytes_array(file_path, array_name)
    if public_key is None:
        sys.exit(1)
    
    console.print(f"\n[bold]Raw bytes (length: {len(public_key)}):[/bold]")
    console.print("[" + ", ".join(f"0x{b:02x}" for b in public_key) + "]")
    
    try:
        ss58 = bytes_to_ss58(public_key)
        console.print(f"\n[bold green]SS58 Address:[/bold green] {ss58}")
    except Exception as e:
        console.print(f"\n[red]Error during conversion: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
