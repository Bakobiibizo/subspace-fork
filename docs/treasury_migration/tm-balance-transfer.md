# Treasury Balance Transfer Migration

## Overview

This document outlines the process for transferring the existing balance from the old Commune DAO treasury address to the new one. This migration follows the treasury address migration and is necessary to ensure all funds are properly transferred to the new treasury address.

## Technical Details

### Current Implementation

Following the treasury address migration (V2 → V3), the governance pallet's storage item `DaoTreasuryAddress` now points to the new treasury address:

```
5GZfkfjD46SmDrnWZbrzkxkYzeJUWKTAB1HvHBurrPc7XcEj
```

However, any existing balance in the old treasury address remains there and needs to be transferred to the new address.

### Migration Plan

The balance transfer migration is implemented as a runtime upgrade that transfers all funds from the old treasury address to the new one. This migration (V3 → V4) will:

1. Retrieve the old treasury address (stored in the migration code)
2. Get the current treasury address from storage
3. Check the balance of the old treasury address
4. Transfer the entire balance to the new treasury address
5. Emit an event for the treasury balance transfer (on-chain audit trail)

### Implementation Details

The migration is implemented in the governance pallet as a storage migration from V3 to V4. The migration code performs the following steps:

1. Retrieves the old treasury address using the public key bytes stored in the migration code
2. Gets the current (new) treasury address from the `DaoTreasuryAddress` storage item
3. Checks if the old treasury has any balance
4. If there is a balance, transfers it to the new treasury address using the Currency trait
5. Emits a `TreasuryBalanceTransferred` event with details of the transfer
6. Increments the storage version to V4 (non-testnet) or V6 (testnet)

The runtime spec version has been incremented to trigger the migration:
- Non-testnet version: 133 → 134
- Testnet version: 516 → 517

### Weight Calculation

The migration code includes a careful analysis of weight calculations to ensure proper resource accounting:

- **Reads (2)**:
  - Reading the old treasury address (from migration data)
  - Reading the `DaoTreasuryAddress` storage item
  - Reading the old treasury balance (included in Currency::transfer)
- **Writes (3)**:
  - Updating the old treasury balance (included in Currency::transfer)
  - Updating the new treasury balance (included in Currency::transfer)
  - Updating the `StorageVersion`

## Building the Runtime

### Prerequisites

- Rust and Cargo installed
- Required dependencies: `protobuf-compiler` and `libclang`

### Build Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/commune-ai/subspace.git
   cd subspace
   ```

2. Build the runtime WASM blob:
   ```bash
   ./scripts/build_runtime_wasm.sh
   ```

3. The WASM blob will be available at:
   ```
   ./runtime_upgrade_wasm/node_subspace_runtime_treasury_balance_transfer.compact.compressed.wasm
   ```

## Deployment Process

### For Validators

1. **Verify the WASM blob**:
   - Download the WASM blob from the official repository
   - Verify the SHA-256 hash matches the published hash

2. **Prepare for the upgrade**:
   - Ensure your node is running the latest version before the upgrade
   - Make a backup of your node data

3. **Monitor the upgrade**:
   - The upgrade will be submitted through the on-chain governance process
   - Once approved, the runtime will automatically upgrade at the specified block
   - No manual intervention is required if you're running an up-to-date node

## Verification Steps

After the migration has been applied, you can verify that it was successful by checking:

### 1. Storage Version

Check that the storage version for the governance pallet has been updated:

```bash
./target/release/node-subspace query storage --pallet governance --name StorageVersion
```

The returned version should be:
- Non-testnet: 4
- Testnet: 6

### 2. Treasury Address

Verify that the treasury address is still correct:

```bash
./target/release/node-subspace query storage --pallet governance --name DaoTreasuryAddress
```

The returned address should match the new treasury address: `5GZfkfjD46SmDrnWZbrzkxkYzeJUWKTAB1HvHBurrPc7XcEj`.

### 3. Old Treasury Balance

Check that the old treasury address has zero balance:

```bash
# Replace OLD_TREASURY_ADDRESS with the actual old treasury address
./target/release/node-subspace query storage --pallet balances --name Account --key <OLD_TREASURY_ADDRESS>
```

The free balance should be zero.

### 4. New Treasury Balance

Check that the new treasury address has received the transferred balance:

```bash
./target/release/node-subspace query storage --pallet balances --name Account --key 5GZfkfjD46SmDrnWZbrzkxkYzeJUWKTAB1HvHBurrPc7XcEj
```

The free balance should include the amount transferred from the old treasury.

### 5. Event Emission

You can verify that the `TreasuryBalanceTransferred` event was emitted by checking the events in the block where the migration was applied:

```bash
# Replace BLOCK_NUMBER with the block number where the migration was applied
./target/release/node-subspace query events --block <BLOCK_NUMBER>
```

Look for an event with the following structure:
```
Event::Governance(TreasuryBalanceTransferred {
    old_address: <OLD_TREASURY_ADDRESS>,
    new_address: 5GZfkfjD46SmDrnWZbrzkxkYzeJUWKTAB1HvHBurrPc7XcEj,
    amount: <TRANSFERRED_AMOUNT>,
})
```

## Troubleshooting

If you encounter any issues with the migration, please check the following:

1. **Node logs**: Look for any errors or warnings related to the migration.
2. **Storage version**: Ensure the storage version has been updated correctly.
3. **Treasury address**: Verify that the treasury address is correct.
4. **Balance transfer**: Check if the balance was transferred correctly.

If you need assistance, please contact the Commune team or open an issue on the GitHub repository.

## Security Considerations

The treasury balance transfer migration has been carefully designed with security in mind:

1. **Balance verification**: The migration checks if there's a balance to transfer before attempting the transfer.
2. **Error handling**: The migration includes comprehensive error handling to ensure it doesn't fail silently.
3. **Event emission**: An event is emitted for the balance transfer, providing an on-chain audit trail.
4. **Idempotency**: The migration is idempotent and can be run multiple times without side effects.
5. **Safe transfer**: The migration uses the safe transfer mechanism from pallet_balances.

## References

- [Treasury Address Migration](./tm-overview.md): Details about the previous migration that updated the treasury address.
- [Security Audit](./tm-security-audit.md): Security considerations for the treasury migrations.
