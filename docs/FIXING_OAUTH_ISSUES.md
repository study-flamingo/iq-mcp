# Debugging OAuth Flow Issue

## Problem
Claude Desktop redirects to: `http://localhost:8000/oauth/callback/oauth/consent?authorization_id=...`
Returns: `{"detail":"Not Found"}`

## Root Cause Analysis

### Environment Variables Issue
Looking at current Railway variables:
- ✅ `IQ_BASE_URL=https://iq-mcp-dev.up.railway.app`
- ✅ `IQ_ENABLE_SUPABASE_AUTH=true`
- ❌ `IQ_USE_OAUTH_PROXY=true` - **This should NOT be set!**
- ❌ `IQ_OAUTH_CLIENT_ID` - **Should be removed!**
- ❌ `IQ_OAUTH_CLIENT_SECRET` - **Should be removed!**

### Server Behavior
The logs show: "🔐 RemoteAuthProvider enabled - OAuth 2.1 with DCR"

But there's confusion about what the actual callback URL structure should be:
- Claude is trying: `http://localhost:8000/oauth/callback/oauth/consent`
- This suggests it's building the URL based on the MCP endpoint structure

## The Issue

1. **Server reports** discovery endpoint at: `https://iq-mcp-dev.up.railway.app/.well-known/oauth-protected-resource/iq`
2. **But** the actual MCP endpoint is at: `https://iq-mcp-dev.up.railway.app/iq`
3. **And** the resource name is: `iq`

When Claude Desktop registers, it likely:
1. Discovers the resource: `https://iq-mcp-dev.up.railway.app/iq`
2. Tries to register with Supabase
3. Gets a callback URL like: `https://iq-mcp-dev.up.railway.app/iq/oauth/callback`
4. But it's somehow resolving to `http://localhost:8000/oauth/callback`

## Possible Issues

### 1. Missing environment variables for RemoteAuthProvider
The FastMCP RemoteAuthProvider needs to know:
- Where to redirect users after consent
- What callback URLs to allow

### 2. ChainedAuthProvider not passing through OAuth routes properly
The ChainedAuthProvider wraps RemoteAuthProvider but might not be exposing the OAuth callback routes correctly.

### 3. FastMCP's OAuth flow is confused about the base URL
When running in stateless HTTP mode, FastMCP might not correctly determine what the public URL is.

## Solutions to Try

### A. Remove Old Environment Variables
Delete these from Railway:
- `IQ_USE_OAUTH_PROXY`
- `IQ_OAUTH_CLIENT_ID`
- `IQ_OAUTH_CLIENT_SECRET`

### B. Add DCR Configuration
Set in Railway:
- `IQ_OAUTH_AUTHORIZATION_SERVERS=https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1`

### C. Fix ChainedAuthProvider
Make sure it properly passes the `get_well_known_routes` from RemoteAuthProvider to the ChainedAuthProvider, and that ChainedAuthProvider registers those routes with the main MCP server.
