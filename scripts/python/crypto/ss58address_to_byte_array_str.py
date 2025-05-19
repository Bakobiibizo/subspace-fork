# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "substrate-interface",
#     "rich",
# ]
# ///
"""
Convert an SS58 address to a formatted byte array string for Rust.

Usage:
    python ss58address_to_byte_array_str.py <ss58_address> [--name VARIABLE_NAME]

Example:
    python ss58address_to_byte_array_str.py 5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY --name MY_ADDRESS
"""

import sys
import argparse
from typing import Optional
from substrateinterface import Keypair
from rich.console import Console

console = Console()

def analyze_public_key(public_key: bytes) -> dict:
    """Analyze the public key for known patterns."""
    result = {
        'is_multisig': False,
        'is_proxy': False,
        'module_name': None,
        'is_all_zeros': all(b == 0 for b in public_key),
        'zero_byte_count': sum(b == 0 for b in public_key),
        'hex': '0x' + public_key.hex()
    }
    
    # Check for module/proxy pattern (starts with 'modl' in ASCII)
    if len(public_key) >= 4 and public_key.startswith(b'modl'):
        result['is_proxy'] = True
        # Try to extract the module name (up to first null byte)
        try:
            null_pos = public_key.find(0)
            if null_pos > 4:  # After 'modl' prefix
                result['module_name'] = public_key[4:null_pos].decode('ascii', errors='replace')
        except:
            pass
    
    # Simple heuristic for potential multi-sig (many zeros but not all)
    zero_ratio = result['zero_byte_count'] / len(public_key)
    result['is_multisig'] = 0.3 < zero_ratio < 0.9  # Not all zeros, but many
    
    return result

def ss58_to_byte_array(ss58_address: str) -> Optional[bytes]:
    """
    Convert an SS58 address to its raw bytes.
    
    Args:
        ss58_address: The SS58-encoded address
        
    Returns:
        The public key as bytes, or None if conversion fails
    """
    try:
        # First try with standard SS58 decoding
        keypair = Keypair(ss58_address=ss58_address)
        public_key = keypair.public_key
        
        # Analyze the public key
        analysis = analyze_public_key(public_key)
        
        # Print analysis
        if analysis['is_proxy']:
            if analysis['module_name']:
                console.print(f"[yellow]Detected proxy account for module: '{analysis['module_name']}'[/yellow]")
            else:
                console.print("[yellow]Detected proxy account (unknown module)[/yellow]")
        elif analysis['is_multisig']:
            console.print("[yellow]Detected potential multi-signature account[/yellow]")
        
        if analysis['zero_byte_count'] > len(public_key) // 2:
            console.print(f"[yellow]Note: Contains {analysis['zero_byte_count']} zero bytes (of {len(public_key)} total)[/yellow]")
        
        # Try to show any ASCII content
        try:
            ascii_part = public_key.split(b'\x00')[0]
            if ascii_part and all(32 <= b <= 126 for b in ascii_part):
                console.print(f"[dim]ASCII content: '{ascii_part.decode('ascii')}'[/dim]")
        except:
            pass
            
        return public_key
        
    except Exception as e:
        console.print(f"[red]Error converting SS58 address: {e}[/red]")
        return None

def format_byte_array(bytes_data: bytes, bytes_per_line: int = 16) -> str:
    """
    Format bytes as a Rust byte array string.
    
    Args:
        bytes_data: The bytes to format
        bytes_per_line: Number of bytes per line
        
    Returns:
        Formatted Rust byte array string
    """
    lines = []
    for i in range(0, len(bytes_data), bytes_per_line):
        chunk = bytes_data[i:i + bytes_per_line]
        hex_bytes = [f"0x{b:02x}" for b in chunk]
        line = "    " + ", ".join(hex_bytes) + ","
        lines.append(line)
    
    return "[\n" + "\n".join(lines) + "\n]"

def main():
    parser = argparse.ArgumentParser(description="Convert SS58 address to Rust byte array")
    parser.add_argument("address", help="SS58 address to convert")
    parser.add_argument("--name", default="PUBLIC_KEY_BYTES",
                      help="Variable name for the byte array (default: PUBLIC_KEY_BYTES)")
    parser.add_argument("--network", type=int, default=42,
                      help="SS58 network ID (default: 42 for Subspace)")
    
    args = parser.parse_args()
    
    console.print(f"[bold]Converting SS58 address:[/bold] {args.address}")
    console.print(f"[dim]Network ID: {args.network} (42 = Subspace)[/dim]\n")
    
    # Convert SS58 to bytes
    public_key = ss58_to_byte_array(args.address)
    if public_key is None:
        sys.exit(1)
    
    # Format the output
    rust_array = format_byte_array(public_key)
    
    # Print the result
    console.print("\n[bold green]Rust Byte Array:[/bold green]")
    print(f"pub const {args.name}: [u8; {len(public_key)}] = {rust_array};\n")
    
    # Show hex representation
    hex_str = '0x' + public_key.hex()
    console.print(f"[bold]Hex:[/bold] {hex_str}")
    
    # Also show the SS58 address for verification
    try:
        keypair = Keypair(public_key=public_key, ss58_format=args.network)
        console.print(f"\n[bold]Verification:[/bold]")
        console.print(f"Original SS58:   {args.address}")
        console.print(f"Reconstructed:   {keypair.ss58_address}")
        console.print(f"Length:          {len(public_key)} bytes")
        
        if keypair.ss58_address != args.address:
            console.print("[yellow]Warning: Reconstructed address doesn't match input![/yellow]")
            
            # Try with different network IDs
            console.print("\n[bold]Trying different network IDs:[/bold]")
            for net_id in [0, 1, 2, 7, 42, 44]:
                try:
                    kp = Keypair(public_key=public_key, ss58_format=net_id)
                    console.print(f"Network {net_id:2d}: {kp.ss58_address}")
                except:
                    pass
                    
    except Exception as e:
        console.print(f"[red]Verification error: {e}[/red]")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Show help if no arguments provided
        parser = argparse.ArgumentParser(description="Convert SS58 address to Rust byte array")
        parser.print_help()
        console.print("\n[red]Error: SS58 address is required[/red]")
        sys.exit(1)
        
    main()