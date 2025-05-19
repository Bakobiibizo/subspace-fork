#!/bin/bash

# Build script for Subspace runtime WebAssembly

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Directories
TARGET_DIR="./target"
WASM_DIR="$TARGET_DIR/release/wbuild/node-subspace-runtime"
OUTPUT_DIR="./runtime_upgrade_wasm"
mkdir -p "$OUTPUT_DIR"

echo -e "${YELLOW}🚀 Building Subspace runtime with testnet feature...${NC}"
cargo build --release --package node-subspace-runtime --target wasm32-unknown-unknown --no-default-features --features testnet

# Check if build was successful
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}❌ Build failed. Trying with runtime-benchmarks feature...${NC}"
    cargo build --release --package node-subspace-runtime --target wasm32-unknown-unknown --no-default-features --features "testnet runtime-benchmarks"
    if [ $? -ne 0 ]; then
        echo "❌ Build failed. Please check the errors above."
        exit 1
    fi
fi

# Copy important files to output directory
echo -e "\n${GREEN}📦 Copying WASM files to output directory...${NC}"
cp "$WASM_DIR/node_subspace_runtime.compact.compressed.wasm" "$OUTPUT_DIR/"
cp "$WASM_DIR/node_subspace_runtime.compact.wasm" "$OUTPUT_DIR/"
cp "$WASM_DIR/node_subspace_runtime.wasm" "$OUTPUT_DIR/"

# Show file info
echo -e "\n${GREEN}📊 File Information:${NC}"
echo "Output directory: $(realpath $OUTPUT_DIR)"
echo ""
ls -lh "$OUTPUT_DIR" | grep "\.wasm"

# Calculate hashes
echo -e "\n${GREEN}🔍 File Hashes:${NC}"
for file in "$OUTPUT_DIR"/*.wasm; do
    echo -n "$(basename "$file") - "
    shasum -a 256 "$file" | cut -d ' ' -f 1
done

# Generate deployment commands
echo -e "\n${GREEN}🚀 Deployment Commands:${NC}"
echo "To use the compressed WASM for production:"
echo "  $(realpath "$OUTPUT_DIR/node_subspace_runtime.compact.compressed.wasm")"
echo ""
echo "To use the uncompressed WASM for development:"
echo "  $(realpath "$OUTPUT_DIR/node_subspace_runtime.compact.wasm")"

echo -e "\n${GREEN}✅ Done!${NC}"