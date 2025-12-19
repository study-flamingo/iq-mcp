#!/bin/bash
# One-command deploy: build, push, and deploy to VM
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# GCP VM Configuration
GCP_PROJECT="dted-ai-agent"
VM_NAME="dted-ai-agent-vm"
VM_ZONE="us-central1-c"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Error handler
handle_error() {
    echo -e "${RED}❌ Deployment failed at step: $1${NC}"
    echo -e "${YELLOW}Troubleshooting:${NC}"
    case "$1" in
        "push")
            echo "  - Check if Docker is running"
            echo "  - Run: gcloud auth configure-docker us-central1-docker.pkg.dev"
            ;;
        "ssh")
            echo "  - Verify VM is running: gcloud compute instances list --project=${GCP_PROJECT}"
            echo "  - Try manual connection: gcloud compute ssh ${VM_NAME} --zone=${VM_ZONE} --project=${GCP_PROJECT}"
            ;;
        "deploy")
            echo "  - SSH worked but deploy script failed"
            echo "  - Check VM logs: gcloud compute ssh ${VM_NAME} --zone=${VM_ZONE} --project=${GCP_PROJECT} --command='cd /opt/iq-mcp && docker compose logs'"
            echo "  - Verify pull-and-deploy.sh exists on VM"
            ;;
    esac
    exit 1
}

# Step 1: Build and push
echo -e "${GREEN}📦 Step 1/2: Building and pushing image...${NC}"
if ! "${PROJECT_ROOT}/deploy/push-image.sh"; then
    handle_error "push"
fi

# Step 2: Deploy on VM
echo ""
echo -e "${GREEN}🌐 Step 2/2: Deploying to VM...${NC}"

# Test SSH connection first using gcloud
if ! gcloud compute ssh "${VM_NAME}" --zone="${VM_ZONE}" --project="${GCP_PROJECT}" --command="echo 'SSH OK'" > /dev/null 2>&1; then
    handle_error "ssh"
fi

# Run deploy script
if ! gcloud compute ssh "${VM_NAME}" --zone="${VM_ZONE}" --project="${GCP_PROJECT}" --command="cd /opt/iq-mcp && ./pull-and-deploy.sh"; then
    handle_error "deploy"
fi

echo ""
echo -e "${GREEN}✅ Full deployment complete!${NC}"
