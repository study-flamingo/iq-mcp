#!/bin/bash
# Pull latest IQ-MCP image and deploy
# This script runs ON THE VM (copy to /opt/iq-mcp/)
#
# Prerequisites on VM:
#   1. Install gcloud CLI
#   2. Configure Docker auth: gcloud auth configure-docker us-central1-docker.pkg.dev

set -e

# Configuration
GCP_PROJECT="dted-ai-agent"
REGION="us-central1"
REPO="iq-mcp"
IMAGE_NAME="iq-mcp"
REGISTRY="${REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPO}"
TAG="${1:-latest}"  # Use first arg or default to 'latest'

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cd /opt/iq-mcp

echo -e "${GREEN}🐳 Pulling IQ-MCP image: ${TAG}${NC}"

# Pull the latest image
docker pull "${REGISTRY}/${IMAGE_NAME}:${TAG}"

# Update docker-compose to use the registry image
echo -e "${YELLOW}🔄 Restarting services...${NC}"

# Stop current containers
docker compose -f docker-compose.prod.yml down

# Start with new image
docker compose -f docker-compose.prod.yml up -d

# Show status
echo -e "${YELLOW}📊 Container status:${NC}"
docker compose -f docker-compose.prod.yml ps

# Show recent logs
echo -e "${YELLOW}📜 Recent logs:${NC}"
docker compose -f docker-compose.prod.yml logs --tail=20 iq-mcp

echo -e "${GREEN}✅ Deployment complete!${NC}"

