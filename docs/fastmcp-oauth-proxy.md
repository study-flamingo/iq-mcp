# FastMCP OAuthProxy Documentation

> Source: https://gofastmcp.com/servers/auth/oauth-proxy

## Overview

OAuthProxy bridges traditional OAuth providers (GitHub, Google, Azure, AWS) that require manual app registration. The proxy presents a DCR-compliant interface to MCP clients while using pre-registered credentials with the upstream provider.

## Critical Configuration Parameters

### base_url (REQUIRED)

**Type:** `AnyHttpUrl | str`

**Description:** Public URL where OAuth endpoints will be accessible, **including any mount path**.

**Example:**
- If your server is at root: `https://api.example.com`
- If mounted under path: `https://api.example.com/mcp`

**Important:** The `base_url` is used to construct OAuth callback URLs and operational endpoints. **When mounting under a path prefix, include that prefix in `base_url`.**

### redirect_path

**Type:** `str`
**Default:** `"/auth/callback"`

**Description:** Path for OAuth callbacks. Must match the redirect URI configured in your OAuth application.

**Full redirect URI:** `{base_url}{redirect_path}`

### issuer_url (OPTIONAL)

**Type:** `AnyHttpUrl | str | None`

**Description:** URL where auth server metadata is located (typically at root level). Use this separately from `base_url` when the OAuth operational endpoints and discovery metadata are at different locations.

**Example Configuration with Path Prefix:**

```python
from fastmcp.server.auth.providers.oauth_proxy import OAuthProxy

auth = OAuthProxy(
    upstream_authorization_endpoint="https://provider.com/oauth/authorize",
    upstream_token_endpoint="https://provider.com/oauth/token",
    upstream_client_id="your-client-id",
    upstream_client_secret="your-client-secret",
    base_url="https://your-server.com/mcp",  # Include path prefix!
    redirect_path="/oauth/callback",  # Default, can customize
    issuer_url="https://your-server.com"  # Optional: root for discovery
)
```

**Resulting URLs:**
- Callback: `https://your-server.com/mcp/oauth/callback`
- Discovery: `https://your-server.com/.well-known/oauth-protected-resource` (if issuer_url set)

## Provider Registration Requirements

When registering your application in the provider's developer console (GitHub Settings, Google Cloud Console, Azure Portal, etc.), configure the redirect URI as:

**Default:** `{your-server-url}/auth/callback`
**Custom:** `{your-server-url}{redirect_path}` (if you set `redirect_path`)
**Development:** `http://localhost:8000/auth/callback`

**CRITICAL:** The redirect URI you configure with your provider must **exactly match** your FastMCP server's URL plus the callback path. If you customize `redirect_path` in the OAuth proxy, update your provider's redirect URI accordingly.

## Implementation Steps

1. Register your application in the provider's developer console
2. Configure the redirect URI as your FastMCP server URL plus your chosen callback path
3. Obtain your credentials: Client ID and Client Secret
4. Note the OAuth endpoints: Authorization URL and Token URL
5. Configure OAuthProxy with **exact matching base_url** including any path prefix
