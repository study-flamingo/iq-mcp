#!/bin/bash
# View logs from VM containers

VM_HOST="iq-mcp-vm"
VM_PATH="/opt/iq-mcp"

# Default to following all logs, or specific service if provided
SERVICE="${1:-}"

if [ -n "$SERVICE" ]; then
    ssh "${VM_HOST}" "cd ${VM_PATH} && sudo docker compose logs -f ${SERVICE}"
else
    ssh "${VM_HOST}" "cd ${VM_PATH} && sudo docker compose logs -f"
fi

