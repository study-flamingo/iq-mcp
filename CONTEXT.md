# OAuth 2.1 DCR Implementation - Complete Context

## 🎯 Mission Summary
Upgraded IQ-MCP server from `SupabaseProvider` to `RemoteAuthProvider` to enable **Dynamic Client Registration (DCR)** for OAuth 2.1 with MCP clients like Claude Desktop.

## 📊 Current Status: PARTIAL SUCCESS

### ✅ What Works:
1. **RemoteAuthProvider deployed** on Railway dev environment
2. **OAuth discovery endpoint** responding correctly at `/.well-known/oauth-protected-resource/iq`
3. **Supabase DCR enabled** with registration endpoint available
4. **Dual authentication** (API key + OAuth) working via ChainedAuthProvider
5. **JWT validation** using RemoteAuthProvider and JWTVerifier

### ❌ Critical Issue:
**Problem:** Claude Desktop redirects to `http://localhost:8000/oauth/callback/oauth/consent?...` instead of Railway URL

**Root Cause:** OAuth redirect_uri is hardcoding localhost, not using `IQ_BASE_URL` or the MCP client's registered redirect_uri

## 🔧 Implementation Details

### Files Modified:

#### 1. src/mcp_knowledge_graph/settings.py
```python
class SupabaseAuthConfig:
    def __init__(
        self,
        *,
        enabled: bool,
        project_url: str | None,
        algorithm: Literal["HS256", "RS256", "ES256"],
        jwt_secret: str | None = None,
        required_scopes: list[str] | None = None,
        authorization_servers: list[str] | None = None,  # NEW
    ) -> None:
        self.enabled = bool(enabled)
        self.project_url = project_url
        self.algorithm = algorithm
        self.jwt_secret = jwt_secret
        self.required_scopes = required_scopes or []
        # Default: [f"{project_url.rstrip('/')}/auth/v1"]
        self.authorization_servers = authorization_servers or []
```

#### 2. src/mcp_knowledge_graph/auth.py
```python
# REMOVED: SupabaseProvider
# NEW: RemoteAuthProvider + JWTVerifier

from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

# JWT verifier for token validation
token_verifier = JWTVerifier(
    jwks_uri=f"{project_url}/auth/v1/.well-known/jwks.json",
    issuer=f"{project_url}/auth/v1",
    audience=base_url,  # Uses IQ_BASE_URL
    required_scopes=supabase_auth.required_scopes or None,
)

# RemoteAuthProvider for DCR
remote_auth = RemoteAuthProvider(
    token_verifier=token_verifier,
    authorization_servers=[AnyHttpUrl(server) for server in supabase_auth.authorization_servers],
    base_url=base_url,  # Uses IQ_BASE_URL
    # NOTE: No allowed_client_redirect_uris parameter
)

providers.append(remote_auth)
```

#### 3. .env.example
```bash
# NEW DCR variables
IQ_OAUTH_AUTHORIZATION_SERVERS=https://your-project.supabase.co/auth/v1

# Existing variables still required
IQ_ENABLE_SUPABASE_AUTH=true
IQ_SUPABASE_AUTH_PROJECT_URL=https://your-project.supabase.co
IQ_SUPABASE_AUTH_ALGORITHM=ES256  # ES256 or RS256 required
IQ_BASE_URL=https://mcp.casimir.ai  # For OAuth audience/redirects
```

### Environment Variables (Railway):
```bash
IQ_ENABLE_SUPABASE_AUTH=true
IQ_SUPABASE_AUTH_PROJECT_URL=https://ahsrjqkbdtgdlgpfewxz.supabase.co
IQ_SUPABASE_AUTH_ALGORITHM=ES256
IQ_BASE_URL=https://iq-mcp-dev.up.railway.app
```

## 🧪 Verification Results

### 1. OAuth Discovery Endpoint ✅
**URL:** `https://iq-mcp-dev.up.railway.app/.well-known/oauth-protected-resource/iq`

**Response:**
```json
{
    "resource": "https://iq-mcp-dev.up.railway.app/iq",
    "authorization_servers": ["https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1"],
    "scopes_supported": [],
    "bearer_methods_supported": ["header"]
}
```

### 2. Supabase DCR Server ✅
**URL:** `https://ahsrjqkbdtgdlgpfewxz.supabase.co/.well-known/oauth-authorization-server/auth/v1`

**Discovery includes:**
- ✅ `registration_endpoint`: `https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1/oauth/clients/register`
- ✅ `authorization_endpoint`: `https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1/oauth/authorize`
- ✅ `token_endpoint`: `https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1/oauth/token`
- ✅ `jwks_uri`: `https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1/.well-known/jwks.json`

### 3. Server Startup ✅
```
INFO:iq-mcp:🔐 RemoteAuthProvider enabled - OAuth 2.1 with DCR
INFO:iq-mcp:   Authorization servers: ['https://ahsrjqkbdtgdlgpfewxz.supabase.co/auth/v1']
INFO:iq-mcp:   JWT algorithm: ES256
INFO:iq-mcp:   Discovery endpoint: https://iq-mcp-dev.up.railway.app/.well-known/oauth-protected-resource
INFO:iq-mcp:   ✨ MCP clients can now self-register via DCR!
INFO:iq-mcp:✅ Authentication: 2 methods (chained)
```

## 🐛 The Critical Bug: Wrong Redirect URI

### What Happens:
1. ✅ Claude Desktop fetches discovery endpoint
2. ✅ Claude registers via DCR with Supabase
3. ✅ Supabase issues authorization request
4. ❌ **Redirects to:** `http://localhost:8000/oauth/callback/oauth/consent?authorization_id=...`
5. ❌ **Result:** `{"detail":"Not Found"}`

### Why This Happens:
The issue is likely in **how FastMCP's RemoteAuthProvider handles redirect URIs**. Based on the callback URL pattern:
```
http://localhost:8000/oauth/callback/oauth/consent
```

This suggests:
1. **Claude Desktop registered** with redirect_uri: `http://localhost:8000/oauth/callback`
2. **FastMCP is appending** `/oauth/consent` to that
3. **But FastMCP server** is listening on Railway, not localhost

**TODO: research this**

### Possible Root Causes:

**A. FastMCP version mismatch**
- Railway uses FastMCP 2.13.3 (from uv.lock)
- But RemoteAuthProvider might need 2.14.0+ for proper redirect handling

**B. Missing FastMCP config**
- Need to tell FastMCP the public URL
- StreamableHTTP transport may not be configured for OAuth

**C. ChainedAuthProvider not passing through routes**
- ChainedAuthProvider wraps RemoteAuthProvider
- Might not expose OAuth callback routes properly

## 🔍 Investigation Commands Needed

### 1. Check FastMCP version on Railway
```bash
# Via railway logs or connect and run:
pip show fastmcp
```

### 2. Check ChainedAuthProvider route handling
The auth provider needs to expose:
- `GET /.well-known/oauth-protected-resource/iq` ✅ (working)
- `GET /.well-known/oauth-authorization-server` (if required)
- `POST /oauth/callback` (for handling callbacks)
- `GET /oauth/consent` (for user approval)

### 3. Check if RemoteAuthProvider needs additional parameters
Looking at FastMCP docs, RemoteAuthProvider might need:
- `resource_name` parameter (optional)
- `resource_documentation` parameter (optional)

## 💡 Recommended Fixes

### Fix 1: Update ChainedAuthProvider to properly handle OAuth routes
```python
# In get_auth_provider(), ensure ChainedAuthProvider properly exposes
# OAuth callback and consent routes from the wrapped providers
```

### Fix 2: Add FastMCP configuration for public URL
```python
# In server.py, ensure FastMCP is configured with:
mcp = FastMCP(
    name="iq-mcp",
    # May need additional OAuth-specific config
)
```

### Fix 3: Manual redirect URI handling
If FastMCP doesn't automatically handle the redirect URI correctly:
```python
# May need to subclass RemoteAuthProvider to override
# redirect URI generation logic
```

## 🚨 Priority: Root Cause Analysis

Before attempting fixes, need to determine:
1. **What redirect_uri did Claude Desktop register?**
2. **What redirect_uri is FastMCP expecting?**
3. **What redirect_uri is Supabase using?**

These should all match `https://iq-mcp-dev.up.railway.app/iq/oauth/callback` (or similar).

## 📋 Next Actions

### Immediate:
1. ✅ **Verify working discovery** - Already confirmed
2. ⏳ **Find why redirect_uri is localhost** - Need to trace OAuth flow
3. ⏳ **Fix redirect_uri mismatch** - Will require code or config change

### Testing Tools:
```bash
# Check OAuth routes
curl -v https://iq-mcp-dev.up.railway.app/health
curl -v https://iq-mcp-dev.up.railway.app/.well-known/oauth-protected-resource/iq

# Check if callback route exists
curl -v https://iq-mcp-dev.up.railway.app/oauth/callback

# Check server logs for redirect_uri errors
```

## 📚 References
- FastMCP RemoteAuthProvider: https://gofastmcp.com/servers/auth/remote-oauth
- OAuth 2.1 + MCP: https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization
- Supabase OAuth: https://supabase.com/docs/guides/auth/oauth-server

---

## 🎯 CRITICAL UPDATE: Unexpected Production State

### 🔍 Discovery on Dev Deployment
After force-pushing and deploying, it turns out:

**Current deployed state uses OAuthProxy** (NOT RemoteAuthProvider)

```bash
# In commit d8acc58:
git log --oneline HEAD~2..HEAD
→ "feat: OAuthProxy for Claude Desktop OAuth 2.1 compatibility"
→ "test: use SupabaseProvider instead of RemoteAuthProvider"
→ "feat: OAuth 2.1 DCR ONLY - remove API key support"
```

### ⚠️ This Explains the Redirect Issue!

**OAuthProxy architecture:**
```python
oauth_proxy = OAuthProxy(
    ...
    redirect_path="/oauth/callback",
    base_url=auth_base_url,  # Needs to be correct
    issuer_url=auth_base_url,
    ...
)
```

### 🔧 Root Cause: Base URL Configuration

**Callback URL pattern from your log:**
```
http://localhost:8000/oauth/callback/oauth/consent?authorization_id=ld7hntgdqlbgs5yzlatwq65ucte5odfi
```

**This shows:**
1. Claude Desktop registered redirect_uri as `http://localhost:8000/oauth/callback`
2. OAuthProxy is working (appending `/oauth/consent`)
3. But `IQ_BASE_URL` is misconfigured → uses default/fallback to localhost

**Expected callback URL:**
```
https://iq-mcp-dev.up.railway.app/oauth/callback/oauth/consent?authorization_id=...
```

### 💡 Solution: Fix IQ_BASE_URL on Railway

The `IQ_BASE_URL` environment variable on Railway needs to include the `/iq` path:
```bash
IQ_BASE_URL=https://iq-mcp-dev.up.railway.app/iq
```

**Or,** if OAuthProxy needs root domain:
```bash
IQ_BASE_URL=https://iq-mcp-dev.up.railway.app
```

### 📝 Current Findings:
- ✅ OAuth discovery works: `/.well-known/oauth-protected-resource/iq`
- ✅ Supabase DCR enabled
- ✅ OAuthProxy handles the flow (not RemoteAuthProvider as initially planned)
- ❌ `IQ_BASE_URL` mismatch causing localhost redirect

### 🚨 Immediate Action:
Check/Update Railway environment variables:
```bash
# Current (likely wrong):
IQ_BASE_URL=https://iq-mcp-dev.up.railway.app

# Try first:
IQ_BASE_URL=https://iq-mcp-dev.up.railway.app/iq

# If that fails, try:
IQ_BASE_URL=https://iq-mcp-dev.up.railway.app
```

---

**Status:** OAuthProxy deployed (not RemoteAuthProvider), discovery ✅, but `IQ_BASE_URL` config issue causes localhost redirect ❌