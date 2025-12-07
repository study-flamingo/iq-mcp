#!/bin/bash
# Quick deploy - sync source only, no rebuild
# Use when only Python code changed (not dependencies)

set -e

VM_HOST="iq-mcp-vm"
VM_PATH="/opt/iq-mcp"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "🚀 Quick deploying source files..."

# Sync only source code
scp -r "${PROJECT_ROOT}/src/" "${VM_HOST}:${VM_PATH}/src/"

# Restart containers (uses cached image layers)
echo "🔄 Restarting containers..."
ssh "${VM_HOST}" "cd ${VM_PATH} && sudo docker compose restart iq-mcp"

echo "✅ Quick deploy complete!"

