#!/usr/bin/env bash
#
# Rotate the IQ-MCP Service Key
# Generates a new key with prefix 'iqmcp_sk_' and updates Railway
#
# Requires Railway CLI: https://docs.railway.app/cli/installation

set -e

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Error: Railway CLI is not installed." >&2
    echo "" >&2
    echo "Install it with one of these methods:" >&2
    echo "  npm install -g @railway/cli" >&2
    echo "  brew install railway (macOS)" >&2
    echo "  curl -fsSL https://railway.app/install.sh | sh" >&2
    echo "" >&2
    echo "More info: https://docs.railway.app/cli/installation" >&2
    exit 1
fi

# Generate a secure random key (32 bytes = 43 base64 chars, URL-safe)
NEW_KEY="iqmcp_sk_$(openssl rand -base64 32 | tr -d '/+=' | head -c 32)"

echo "🔐 Rotating IQ-MCP Service Key..."
echo ""
echo "New key: iqmcp_sk_[REDACTED_KEY]"
echo ""

# Update Railway environment variable
echo "📤 Updating Railway environment variable..."
railway variables set "IQ_API_KEY=$NEW_KEY"

echo ""
echo "✅ Service key rotated successfully!"
echo ""
echo "⚠️  Important: Update your MCP client configurations with the new key."
echo "   The old key will stop working after Railway redeploys."
