#!/usr/bin/env bash
#
# Rotate the IQ-MCP Service Key
# Generates a new key with prefix 'iqmcp_sk_' and updates Railway
#
# Usage:
#   ./rotate-service-key.sh [--prod|--dev|--all]
#
# Options:
#   --prod    Update production environment only
#   --dev     Update dev environment only
#   --all     Update both prod and dev environments (default)
#
# Requires Railway CLI: https://docs.railway.app/cli/installation

set -e

# Parse arguments
ENVIRONMENTS=()
if [[ $# -eq 0 ]]; then
    # Default: update all environments
    ENVIRONMENTS=("prod" "dev")
elif [[ "$1" == "--prod" ]]; then
    ENVIRONMENTS=("prod")
elif [[ "$1" == "--dev" ]]; then
    ENVIRONMENTS=("dev")
elif [[ "$1" == "--all" ]]; then
    ENVIRONMENTS=("prod" "dev")
else
    echo "❌ Error: Invalid argument '$1'" >&2
    echo "" >&2
    echo "Usage: $0 [--prod|--dev|--all]" >&2
    echo "" >&2
    echo "Options:" >&2
    echo "  --prod    Update production environment only" >&2
    echo "  --dev     Update dev environment only" >&2
    echo "  --all     Update both prod and dev environments (default)" >&2
    exit 1
fi

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

# Redact key for display (show first 12 and last 4 chars after prefix)
KEY_SUFFIX="${NEW_KEY#iqmcp_sk_}"
REDACTED_KEY="iqmcp_sk_${KEY_SUFFIX:0:12}...${KEY_SUFFIX: -4}"

echo "Rotating IQ-MCP Service Key..."
echo ""
echo "New key: $REDACTED_KEY"
echo ""

# Update each specified environment
for env in "${ENVIRONMENTS[@]}"; do
    echo "Updating $env environment..."
    railway environment "$env" && railway service "iq-mcp:$env" && railway variables -e "$env" --set "IQ_API_KEY=$NEW_KEY"
done

echo ""
echo "Service key rotated successfully!"
echo "Environments updated: ${ENVIRONMENTS[*]}"
echo ""
echo "Important: Update your MCP client configurations with the new key."
echo "The old key will stop working after Railway redeploys."
