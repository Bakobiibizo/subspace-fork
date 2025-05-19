# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "substrate-interface",
#     "rich",
# ]
# ///
from substrateinterface import SubstrateInterface, Keypair
from rich.console import Console

console = Console()

# Connect to the node
substrate = SubstrateInterface(url="ws://127.0.0.1:9944")

def create_multi_sig():
    # Create or load keypairs
    alice = Keypair.create_from_uri("//Alice")
    bob = Keypair.create_from_uri("//Bob")
    charlie = Keypair.create_from_uri("//Charlie")
    
    # Define threshold and signatories
    threshold = 2
    signatories = [alice.ss58_address, bob.ss58_address, charlie.ss58_address]
    
    # Create the multi-signature address
    multi_address = substrate.generate_multisig_account(
        signatories=signatories,
        threshold=threshold
    )
    
    console.print(f"Multi-signature address: {multi_address}", style="green")
    console.print(f"Signatories: {signatories}", style="blue")
    console.print(f"Threshold: {threshold}", style="blue")
    return {
        "address": multi_address,
        "signatories": signatories,
        "threshold": threshold
    }

if __name__ == "__main__":
    create_multi_sig()
    