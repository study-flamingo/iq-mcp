#
# Rotate the IQ-MCP Service Key
# Generates a new key with prefix 'iqmcp_sk_' and updates Railway
#

$ErrorActionPreference = "Stop"

# Generate a secure random key (32 bytes, base64 URL-safe)
$bytes = New-Object byte[] 32
[System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
$randomPart = [Convert]::ToBase64String($bytes) -replace '[/+=]', '' | Select-Object -First 1
$randomPart = $randomPart.Substring(0, [Math]::Min(32, $randomPart.Length))
$newKey = "iqmcp_sk_$randomPart"

Write-Host "🔐 Rotating IQ-MCP Service Key..." -ForegroundColor Cyan
Write-Host ""
Write-Host "New key: $newKey" -ForegroundColor Yellow
Write-Host ""

# Update Railway environment variable
Write-Host "📤 Updating Railway environment variable..." -ForegroundColor Cyan
railway variables set "IQ_API_KEY=$newKey"

Write-Host ""
Write-Host "✅ Service key rotated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  Important: Update your MCP client configurations with the new key." -ForegroundColor Yellow
Write-Host "   The old key will stop working after Railway redeploys."
