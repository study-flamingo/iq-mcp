#!/bin/bash
# Build and push IQ-MCP Docker image to Google Artifact Registry
# 
# Prerequisites:
#   1. Install gcloud CLI: https://cloud.google.com/sdk/docs/install
#   2. Authenticate: gcloud auth login
#   3. Configure Docker: gcloud auth configure-docker us-central1-docker.pkg.dev
#
# First-time setup (run once):
#   gcloud artifacts repositories create iq-mcp \
#     --repository-format=docker \
#     --location=us-central1 \
#     --description="IQ-MCP Docker images"

set -e

# Configuration
GCP_PROJECT="dted-ai-agent"  # Your GCP project ID
REGION="us-central1"
REPO="iq-mcp"
IMAGE_NAME="iq-mcp"
REGISTRY="${REGION}-docker.pkg.dev/${GCP_PROJECT}/${REPO}"

# Get version from pyproject.toml or use 'latest'
VERSION=$(grep -m1 'version = ' pyproject.toml | sed 's/.*version = "\(.*\)"/\1/' 2>/dev/null || echo "latest")
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🐳 Building IQ-MCP Docker image${NC}"
echo -e "   Registry: ${REGISTRY}"
echo -e "   Version:  ${VERSION}"

cd "${PROJECT_ROOT}"

# Pre-flight checks
RED='\033[0;31m'

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed or not in PATH${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon is not running${NC}"
    echo "   Start Docker Desktop or run: sudo systemctl start docker"
    exit 1
fi

if ! docker pull ${REGISTRY}/${IMAGE_NAME}:latest &> /dev/null; then
    echo -e "${YELLOW}⚠️  Cannot access registry (may need: gcloud auth configure-docker ${REGION}-docker.pkg.dev)${NC}"
    # Continue anyway - push will fail with better error if auth is wrong
fi

# Build with both version tag and latest
echo -e "${YELLOW}📦 Building image...${NC}"
docker build -t "${REGISTRY}/${IMAGE_NAME}:${VERSION}" \
             -t "${REGISTRY}/${IMAGE_NAME}:latest" \
             .

# Push both tags
echo -e "${YELLOW}🚀 Pushing to Artifact Registry...${NC}"
docker push "${REGISTRY}/${IMAGE_NAME}:${VERSION}"
docker push "${REGISTRY}/${IMAGE_NAME}:latest"

echo -e "${GREEN}✅ Image pushed successfully!${NC}"
echo -e ""
echo -e "To deploy on VM, run:"
echo -e "  ssh iq-mcp-vm 'cd /opt/iq-mcp && ./pull-and-deploy.sh'"
echo -e ""
echo -e "Or use the combined command:"
echo -e "  ./deploy/push-and-deploy.sh"

