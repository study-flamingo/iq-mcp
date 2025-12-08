#!/bin/bash
# IQ-MCP SSL Certificate Setup
# Run this to obtain Let's Encrypt certificates for mcp.casimir.ai

set -e

DOMAIN="mcp.casimir.ai"
APP_DIR="/opt/iq-mcp"

echo "🔐 SSL Certificate Setup for ${DOMAIN}"
echo "======================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo -e "${RED}Error: certbot is not installed. Run setup-vm.sh first.${NC}"
    exit 1
fi

# Stop nginx if running (to free port 80)
echo -e "${YELLOW}Stopping any running containers...${NC}"
cd $APP_DIR
docker compose down 2>/dev/null || true

# Obtain certificate using standalone mode
echo -e "${GREEN}📜 Obtaining SSL certificate for ${DOMAIN}...${NC}"
sudo certbot certonly \
    --standalone \
    --non-interactive \
    --agree-tos \
    --email admin@casimir.ai \
    -d $DOMAIN

# Copy certificates to nginx directory
echo -e "${GREEN}📁 Copying certificates to nginx directory...${NC}"
sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $APP_DIR/nginx/ssl/
sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $APP_DIR/nginx/ssl/
sudo chown -R $USER:$USER $APP_DIR/nginx/ssl/
chmod 600 $APP_DIR/nginx/ssl/privkey.pem

echo ""
echo -e "${GREEN}✅ SSL certificate setup complete!${NC}"
echo ""
echo "Certificates installed at:"
echo "  - $APP_DIR/nginx/ssl/fullchain.pem"
echo "  - $APP_DIR/nginx/ssl/privkey.pem"
echo ""
echo "Next step: Start the application"
echo "  cd $APP_DIR && docker compose up -d"
echo ""

# Set up auto-renewal cron job
echo -e "${YELLOW}Setting up certificate auto-renewal...${NC}"
CRON_CMD="0 3 * * * certbot renew --quiet && cp /etc/letsencrypt/live/$DOMAIN/*.pem $APP_DIR/nginx/ssl/ && docker compose -f $APP_DIR/docker-compose.yml restart nginx"

# Check if cron job already exists
if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo -e "${GREEN}✓ Auto-renewal cron job added${NC}"
else
    echo -e "${GREEN}✓ Auto-renewal cron job already exists${NC}"
fi

