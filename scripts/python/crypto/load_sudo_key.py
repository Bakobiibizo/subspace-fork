# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "substrate-interface",
#     "rich",
# ]
# ///
from substrateinterface import SubstrateInterface, Keypair, KeypairType
from substrateinterface.utils.ss58 import ss58_encode
from rich.console import Console
from pathlib import Path
import json

console = Console()

def load_sudo_key():
    key_dir = Path.home() / ".commune" / "key"
    input_key = input("Enter sudo key name: ")
    key_path = key_dir / f"{input_key}.json"
    
    if not key_path.exists():
        console.print(f"Key {input_key} not found", style="red")
        return None
    
    key_data = json.loads(key_path.read_text())["data"]
    key_dict = json.loads(key_data)
    keypair = Keypair(
        ss58_address=key_dict["ss58_address"],
        private_key=key_dict["private_key"],
        public_key=key_dict["public_key"]
    )
    console.print(f"Loaded sudo key {input_key}", style="green")
    return keypair

if __name__ == "__main__":
    sudo_key = load_sudo_key()
    if sudo_key:
        multi_sig_info = create_multi_sig()
        # You can use sudo_key here if needed for admin operations