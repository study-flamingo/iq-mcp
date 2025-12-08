#!/bin/bash
# IQ-MCP VM Setup Script
# Run this on a fresh Ubuntu/Debian VM to set up IQ-MCP

set -e

echo "🚀 IQ-MCP VM Setup Script"
echo "========================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}Warning: Running as root. Consider using a non-root user.${NC}"
fi

# Update system
echo -e "${GREEN}📦 Updating system packages...${NC}"
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo -e "${GREEN}🐳 Installing Docker...${NC}"
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}⚠️  You may need to log out and back in for Docker group to take effect${NC}"
else
    echo -e "${GREEN}✓ Docker already installed${NC}"
fi

# Install Docker Compose plugin if not present
if ! docker compose version &> /dev/null; then
    echo -e "${GREEN}📦 Installing Docker Compose plugin...${NC}"
    sudo apt-get install -y docker-compose-plugin
else
    echo -e "${GREEN}✓ Docker Compose already installed${NC}"
fi

# Install certbot for SSL
if ! command -v certbot &> /dev/null; then
    echo -e "${GREEN}🔐 Installing Certbot...${NC}"
    sudo apt-get install -y certbot
else
    echo -e "${GREEN}✓ Certbot already installed${NC}"
fi

# Install git if not present
if ! command -v git &> /dev/null; then
    echo -e "${GREEN}📦 Installing Git...${NC}"
    sudo apt-get install -y git
fi

# Create app directory
APP_DIR="/opt/iq-mcp"
echo -e "${GREEN}📁 Setting up application directory at ${APP_DIR}...${NC}"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Create required directories
mkdir -p $APP_DIR/data
mkdir -p $APP_DIR/data/backups
mkdir -p $APP_DIR/nginx/ssl
mkdir -p $APP_DIR/nginx/certbot
mkdir -p $APP_DIR/nginx/conf.d

echo ""
echo -e "${GREEN}✅ VM setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Clone your repository to $APP_DIR"
echo "2. Copy deploy/env.production.template to $APP_DIR/.env and fill in secrets"
echo "3. Run SSL certificate setup (see deploy/setup-ssl.sh)"
echo "4. Start the application: cd $APP_DIR && docker compose up -d"
echo ""

