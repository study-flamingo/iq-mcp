#!/bin/bash
# IQ-MCP Deployment Script
# Syncs local changes to VM and rebuilds containers

set -e

# Configuration
VM_HOST="iq-mcp-vm"
VM_PATH="/opt/iq-mcp"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying IQ-MCP to ${VM_HOST}${NC}"

# Files to sync
SYNC_FILES=(
    "src/"
    "pyproject.toml"
    "Dockerfile"
    "docker-compose.yml"
    "nginx/"
)

# Sync files
echo -e "${YELLOW}📦 Syncing files...${NC}"
for file in "${SYNC_FILES[@]}"; do
    if [ -e "${PROJECT_ROOT}/${file}" ]; then
        echo "  → ${file}"
        scp -r "${PROJECT_ROOT}/${file}" "${VM_HOST}:${VM_PATH}/${file}"
    fi
done

# Rebuild and restart
echo -e "${YELLOW}🔨 Rebuilding containers...${NC}"
ssh "${VM_HOST}" "cd ${VM_PATH} && sudo docker compose build && sudo docker compose up -d"

# Show status
echo -e "${YELLOW}📊 Container status:${NC}"
ssh "${VM_HOST}" "cd ${VM_PATH} && sudo docker compose ps"

echo -e "${GREEN}✅ Deployment complete!${NC}"

