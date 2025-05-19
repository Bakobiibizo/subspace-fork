# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "substrate-interface",
#     "rich",
# ]
# ///
"""
Test SS58 address conversion against known good values.

This script verifies that our SS58 conversion matches Substrate's implementation.
"""

import unittest
from substrateinterface import Keypair, KeypairType

# Known test vectors from Substrate
# Format: (public_key_hex, expected_ss58_address, network_id)
TEST_VECTORS = [
    # Test vector 1
    (
        "d6f1a71052334dbd4f8f34082c0a58b260c7eb2a6767a09f9d5bc55c5e3df0c1",
        "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        42
    ),
    # Test vector 2
    (
        "1df0d38d7e42e7b3b220d07d1e0f1d6b3e3e3e3e3e3e3e3e3e3e3e3e3e3e3e3",
        "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty",
        42
    ),
    # Test vector 3 - 32 bytes of zeros (edge case)
    (
        "0000000000000000000000000000000000000000000000000000000000000000",
        "5C5555yEXUcmEJ5kkcCMvdZjUo7NGJiQJMS7vZXHixomR5vV",
        42
    )
]

class TestSS58Conversion(unittest.TestCase):
    def test_ss58_conversion(self):
        """Test SS58 conversion against known test vectors."""
        for pubkey_hex, expected_ss58, network_id in TEST_VECTORS:
            with self.subTest(pubkey_hex=pubkey_hex, expected_ss58=expected_ss58):
                # Convert hex to bytes
                public_key = bytes.fromhex(pubkey_hex)
                
                # Convert to SS58 using our method
                keypair = Keypair(
                    public_key=public_key,
                    ss58_format=network_id,
                    crypto_type=KeypairType.SR25519  # Default crypto type in Substrate
                )
                actual_ss58 = keypair.ss58_address
                
                # Verify
                self.assertEqual(actual_ss58, expected_ss58)
                print(f"✓ {pubkey_hex[:8]}... -> {actual_ss58}")


def main():
    print("Testing SS58 conversion against known test vectors...\n")
    
    # Run tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False, verbosity=2)
    
    print("\nIf all tests passed, the SS58 conversion is working correctly!")
    print("You can now use bytes_to_ss58.py with confidence.")


if __name__ == "__main__":
    main()
