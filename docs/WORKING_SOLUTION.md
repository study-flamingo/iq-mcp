# Working Solution for IQ-MCP with Claude Desktop

## Status: API Key Auth Works ✅, OAuth 2.1 DCR Needs Investigation ❌

## Option 1: Use API Key (RECOMMENDED - Works Now)

**This is the confirmed working solution for Claude Desktop.**

### Setup Steps:

1. **Get your API key** (already available in Railway):
   ```bash
   # Your API key is: iqmcp_sk_Bb7NwPIYGODswm69EdefBBacUoYxlHYE
   ```

2. **Configure Claude Desktop**:
   - Open Claude Desktop settings
   - Add MCP server
   - Type: **HTTP**
   - URL: `https://iq-mcp-dev.up.railway.app`
   - Headers:
     ```
     Authorization: Bearer iqmcp_sk_Bb7NwPIYGODswm69EdefBBacUoYxlHYE
     ```

3. **Restart Claude Desktop** and test!

### Why API Key Works:
- ✅ ChainedAuthProvider exposes API key verification
- ✅ HTTP Bearer token auth is standard
- ✅ No OAuth flow complexity

---

## Option 2: OAuth 2.1 DCR (Investigation Needed)

**Current Status: Attempting to use OAuth 2.1 with Dynamic Client Registration**

### What We Implemented:
- ✅ RemoteAuthProvider configured
- ✅ JWTVerifier for Supabase tokens
- ✅ OAuth discovery endpoint at `/.well-known/oauth-protected-resource`
- ✅ Supabase DCR endpoints available

### What's Broken:
- ❌ Claude Desktop redirects to `http://localhost:8000/oauth/callback/...`
- ❌ Expected: Claude should go to Supabase for auth
- ❌ Debug logs for RemoteAuthProvider not appearing

### Root Cause Theories:

**Theory 1: ChainedAuthProvider Interference**
The ChainedAuthProvider might not properly expose OAuth routes from RemoteAuthProvider.

**Theory 2: Claude Desktop DCR Support**
Claude Desktop might not support OAuth 2.1 DCR discovery flow.

**Theory 3: Configuration Mismatch**
Some environment variable or FastMCP configuration is preventing RemoteAuthProvider from initializing.

### What We Know:
1. **Discovery endpoint works**: `https://iq-mcp-dev.up.railway.app/.well-known/oauth-protected-resource` returns correct metadata
2. **Supabase DCR is enabled**: Registration endpoint exists
3. **Server runs correctly**: Health check passes, API key works
4. **But OAuth flow fails**: Claude tries localhost instead of Supabase

### Next Steps to Investigate:
1. Test with **only** RemoteAuthProvider (disable API key temporarily)
2. Check if Claude Desktop has OAuth configuration options
3. Test with MCP Inspector CLI for OAuth support
4. Review FastMCP RemoteAuthProvider source for Claude Desktop compatibility

---

## Option 3: Use Different MCP Client

Some MCP clients have better OAuth 2.1 support:

### MCP Inspector (Testing):
```bash
npx @modelcontextprotocol/inspector --cli https://iq-mcp-dev.up.railway.app \
  --transport http \
  --method tools/list \
  --header "Authorization: Bearer iqmcp_sk_Bb7NwPIYGODswm69EdefBBacUoYxlHYE"
```

### Cursor:
Cursor has native MCP support that might handle OAuth better.

---

## Quick Comparison:

| Feature | API Key | OAuth DCR |
|---------|---------|-----------|
| **Works with Claude** | ✅ Yes | ❌ No (yet) |
| **User friendly** | 🔧 Manual setup | 🔄 Automatic discovery |
| **Security** | Good (if kept secret) | Better (per-user auth) |
| **Implementation** | Simple | Complex |
| **DCR support** | N/A | ✅ Implemented but not working |

---

## Recommendation:

**Use Option 1 (API Key)** for immediate functionality. The server is fully operational and all IQ-MCP tools work correctly with API key authentication.

**OAuth 2.1 DCR** is implemented on the server side but Claude Desktop appears to have issues with the flow. This requires:
- Further debugging of the authentication flow
- Possibly a different MCP client that fully supports OAuth 2.1
- Or manual OAuth client configuration instead of DCR

---

## Environment Variables (Current):

```
# Required for API key auth:
IQ_API_KEY=iqmcp_sk_Bb7NwPIYGODswm69EdefBBacUoYxlHYE

# Required (irrelevant for API key but set):
IQ_ENABLE_SUPABASE_AUTH=true
IQ_BASE_URL=https://iq-mcp-dev.up.railway.app

# No client credentials needed for DCR!
# No IQ_OAUTH_CLIENT_ID or IQ_OAUTH_CLIENT_SECRET required
```

---

## To Switch Between Auth Methods:

**API Key only**: Set IQ_API_KEY and leave IQ_ENABLE_SUPABASE_AUTH=true
**OAuth only**: Remove IQ_API_KEY and keep IQ_ENABLE_SUPABASE_AUTH=true
**Both**: Keep both (current config - ChainedAuthProvider)

---

## Test the Working Solution:

```bash
# Test connection
curl -X POST https://iq-mcp-dev.up.railway.app \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer iqmcp_sk_Bb7NwPIYGODswm69EdefBBacUoYxlHYE" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Test discovery
curl https://iq-mcp-dev.up.railway.app/.well-known/oauth-protected-resource

# Health check
curl https://iq-mcp-dev.up.railway.app/health
```

All tests should pass. Now configure Claude Desktop with the API key as shown above.
