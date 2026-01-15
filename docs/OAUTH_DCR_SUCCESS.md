# OAuth 2.1 with DCR - Deployment Success ✅

**Deployment:** https://iq-mcp-dev.up.railway.app
**Date:** January 13, 2026
**Status:** WORKING

---

## ✅ Verification Results

### 1. OAuth Discovery Endpoint
**URL:** `https://iq-mcp-dev.up.railway.app/.well-known/oauth-protected-resource/iq`

**Response:**
```json
{
    "resource": "https://iq-mcp-dev.up.railway.app/iq",
    "authorization_servers": [
        "https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1"
    ],
    "scopes_supported": [],
    "bearer_methods_supported": ["header"]
}
```

✅ **Status:** Working - MCP clients can auto-discover OAuth configuration

---

### 2. Supabase Authorization Server
**Discovery URL:** `https://ahsrjqkbdtgdlgpfewxz.supabase.co/.well-known/oauth-authorization-server/auth/v1`

**Key Endpoints:**
- ✅ Authorization: `https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1/oauth/authorize`
- ✅ Token: `https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1/oauth/token`
- ✅ **DCR Registration:** `https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1/oauth/clients/register`
- ✅ JWKS: `https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1/.well-known/jwks.json`

**Supported Features:**
- ✅ Dynamic Client Registration (DCR)
- ✅ Authorization Code Grant with PKCE
- ✅ ES256 JWT Signing
- ✅ Public clients (`none` auth method)

---

### 3. Server Logs Confirmation
```
INFO:iq-mcp:🔑 Static API key auth enabled for: joel
INFO:iq-mcp:🔐 RemoteAuthProvider enabled - OAuth 2.1 with DCR
INFO:iq-mcp:   Authorization servers: ['https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1']
INFO:iq-mcp:   JWT algorithm: ES256
INFO:iq-mcp:   Discovery endpoint: https://iq-mcp-dev.up.railway.app/.well-known/oauth-protected-resource
INFO:iq-mcp:   ✨ MCP clients can now self-register via DCR!
INFO:iq-mcp:✅ Authentication: 2 methods (chained)
```

---

## 🎯 What This Means

### MCP Clients Can Now:
1. **Auto-discover** OAuth configuration via `/.well-known/oauth-protected-resource/iq`
2. **Self-register** via Supabase DCR endpoint (no manual client setup needed)
3. **Authenticate users** through Supabase OAuth flow
4. **Access tools** using JWT bearer tokens

### Dual Authentication Works:
- **API Key** (StaticTokenVerifier) - for backwards compatibility
- **OAuth 2.1** (RemoteAuthProvider + Supabase DCR) - for MCP clients

ChainedAuthProvider tries both methods automatically.

---

## 🧪 Testing the OAuth Flow

### Option 1: MCP Inspector CLI
```bash
npx @modelcontextprotocol/inspector --cli https://iq-mcp-dev.up.railway.app/iq \
  --transport http \
  --method tools/list
```

**Expected behavior:**
1. Inspector requests tools without auth
2. Server returns 401 with OAuth error
3. Inspector should attempt OAuth discovery
4. (May not fully support DCR - this is a known limitation)

### Option 2: Claude Desktop (Recommended)
Add to Claude Desktop MCP config (`~/.claude/mcp.json` or similar):

```json
{
  "mcpServers": {
    "iq-mcp-dev": {
      "type": "http",
      "url": "https://iq-mcp-dev.up.railway.app/iq"
    }
  }
}
```

**Expected flow:**
1. Claude Desktop fetches discovery endpoint
2. Registers itself via DCR at Supabase
3. Opens browser to Supabase authorization page
4. User approves access
5. Claude Desktop receives access token
6. Claude can now use IQ-MCP tools

### Option 3: API Key (Bypass OAuth)
```bash
npx @modelcontextprotocol/inspector --cli https://iq-mcp-dev.up.railway.app/iq \
  --transport http \
  --header "Authorization: Bearer YOUR_API_KEY" \
  --method tools/list
```

---

## 📝 Code Changes Summary

### Files Modified:
1. **src/mcp_knowledge_graph/settings.py**
   - Added `authorization_servers` field to SupabaseAuthConfig
   - Auto-populates from `project_url/auth/v1`
   - Loads optional `IQ_OAUTH_AUTHORIZATION_SERVERS` env var

2. **src/mcp_knowledge_graph/auth.py**
   - Replaced `SupabaseProvider` with `RemoteAuthProvider`
   - Uses `JWTVerifier` for token validation (same logic)
   - Exposes OAuth discovery endpoint via RemoteAuthProvider
   - Maintains ChainedAuthProvider for dual auth

3. **.env.example**
   - Documented DCR configuration
   - Updated comments to reflect OAuth 2.1 capabilities

### Environment Variables:
**Required (existing):**
- `IQ_ENABLE_SUPABASE_AUTH=true`
- `IQ_SUPABASE_AUTH_PROJECT_URL=https://your-project.supabase.co`
- `IQ_SUPABASE_AUTH_ALGORITHM=ES256`
- `IQ_BASE_URL=https://iq-mcp-dev.up.railway.app`

**Optional (auto-configured):**
- `IQ_OAUTH_AUTHORIZATION_SERVERS` - defaults to `{project_url}/auth/v1`

---

## 🔒 Security Notes

### What Changed:
- ✅ **Same JWT validation** - JWTVerifier uses identical JWKS/issuer/audience checks
- ✅ **Same security guarantees** - No reduction in security
- ✅ **API key fallback** - ChainedAuthProvider preserves API key auth
- ✅ **No secrets exposed** - Discovery endpoint only contains public metadata

### What's New:
- ✅ **DCR enabled** - Clients can self-register (requires user approval in Supabase)
- ✅ **Discovery metadata** - OAuth configuration exposed at well-known URL
- ✅ **Better MCP compliance** - Follows MCP OAuth 2.1 specification

### Threat Model:
- ⚠️ **DCR allows any client to register** - User must approve each one in Supabase UI
- ✅ **Redirect URI validation** - Supabase validates all redirect URIs during registration
- ✅ **User approval required** - Each client needs user consent before getting tokens
- ✅ **Token validation unchanged** - Same security as before

---

## 🚀 Next Steps

1. **Test with Claude Desktop** - Add the server and verify OAuth flow works
2. **Monitor Supabase Dashboard** - Check for DCR client registrations
3. **Document user onboarding** - How to connect MCP clients with DCR
4. **Consider production** - Deploy to main branch once tested

---

## 📚 References

- [FastMCP RemoteAuthProvider Docs](https://gofastmcp.com/servers/auth/remote-oauth)
- [Supabase OAuth 2.1 Server](https://supabase.com/docs/guides/auth/oauth-server)
- [MCP Authentication Spec](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [Supabase MCP Authentication Guide](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication)

---

## ✅ Success Criteria Met

- [x] OAuth discovery endpoint responds correctly
- [x] Supabase DCR registration endpoint available
- [x] RemoteAuthProvider initialized successfully
- [x] API key authentication still works (dual auth)
- [x] No breaking changes to existing clients
- [x] Server starts without errors
- [x] Logs confirm DCR is enabled

**Status:** Ready for testing with MCP clients! 🎉
