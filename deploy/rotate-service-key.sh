#!/usr/bin/env bash
#
# Rotate the IQ-MCP Service Key
# Generates a new key with prefix 'iqmcp_sk_' and updates Railway
#

set -e

# Generate a secure random key (32 bytes = 43 base64 chars, URL-safe)
NEW_KEY="iqmcp_sk_$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)"

echo "🔐 Rotating IQ-MCP Service Key..."
echo ""
echo "New key: $NEW_KEY"
echo ""

# Update Railway environment variable
echo "📤 Updating Railway environment variable..."
railway variables set "IQ_API_KEY=$NEW_KEY"

echo ""
echo "✅ Service key rotated successfully!"
echo ""
echo "⚠️  Important: Update your MCP client configurations with the new key."
echo "   The old key will stop working after Railway redeploys."
