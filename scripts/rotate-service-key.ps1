#
# Rotate the IQ-MCP Service Key
# Generates a new key with prefix 'iqmcp_sk_' and updates Railway
#
# Usage:
#   .\rotate-service-key.ps1 [-Prod] [-Dev] [-All]
#
# Options:
#   -Prod    Update production environment only
#   -Dev     Update dev environment only
#   -All     Update both prod and dev environments (default)
#

param(
    [switch]$Prod,
    [switch]$Dev,
    [switch]$All
)

$ErrorActionPreference = "Stop"

# Parse arguments and determine which environments to update
$environments = @()
if ($Prod) {
    $environments += "prod"
} elseif ($Dev) {
    $environments += "dev"
} elseif ($All) {
    $environments = @("prod", "dev")
} else {
    # Default: update all environments
    $environments = @("prod", "dev")
}

# Generate a secure random key (32 bytes, base64 URL-safe)
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$bytes = New-Object byte[] 32
$rng.GetBytes($bytes)
$randomPart = [Convert]::ToBase64String($bytes) -replace '[/+=]', '' | Select-Object -First 1
$randomPart = $randomPart.Substring(0, [Math]::Min(32, $randomPart.Length))
$newKey = "iqmcp_sk_$randomPart"

# Redact key for display (show first 12 and last 4 chars after prefix)
$keySuffix = $randomPart
$redactedKey = "iqmcp_sk_$($keySuffix.Substring(0, 12))...$($keySuffix.Substring($keySuffix.Length - 4))"

Write-Host "Rotating IQ-MCP Service Key..." -ForegroundColor Cyan
Write-Host ""
Write-Host "New key: $redactedKey" -ForegroundColor Yellow
Write-Host ""

# Update each specified environment
foreach ($env in $environments) {
    Write-Host "Updating $env environment..." -ForegroundColor Cyan
    railway environment $env
    railway service "iq-mcp:$env"
    railway variables -e $env --set "IQ_API_KEY=$newKey"
}

Write-Host ""
Write-Host "Service key rotated successfully!" -ForegroundColor Green
Write-Host "Environments updated: $($environments -join ', ')" -ForegroundColor Green
Write-Host ""
Write-Host "Important: Update your MCP client configurations with the new key." -ForegroundColor Yellow
Write-Host "The old key will stop working after Railway redeploys."
