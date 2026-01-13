# OAuth 2.1 with RemoteAuthProvider Implementation Plan (REVISED)

## Executive Summary

**Goal:** Replace current SupabaseProvider with FastMCP's **RemoteAuthProvider** to enable proper OAuth 2.1 with Dynamic Client Registration (DCR) for MCP clients like Claude Desktop.

**Current State (v1.5.0):**
- Uses **SupabaseProvider** from FastMCP (JWT validation via JWKS)
- ChainedAuthProvider wrapper for dual auth (OAuth + API keys)
- ~197 lines in auth.py

**Why RemoteAuthProvider?**
Based on FastMCP documentation and Supabase's OAuth 2.1 Server docs:

1. **Dynamic Client Registration (DCR)**: MCP clients can self-register automatically
   - No manual OAuth client setup required
   - MCP clients like Claude Desktop auto-configure via discovery endpoints

2. **Better MCP Standard Compliance**: Exposes OAuth protected resource metadata at `/.well-known/oauth-protected-resource`
   - SupabaseProvider only validates tokens
   - RemoteAuthProvider provides full OAuth 2.1 resource server capabilities

3. **Supabase Native Support**: Supabase Auth has DCR enabled since Nov 2025
   - Discovery endpoint: `https://<project>.supabase.co/.well-known/oauth-authorization-server/auth/v1`
   - Supports PKCE, automatic token rotation, RLS integration

4. **Recommended by Supabase**: Their MCP authentication guide specifically mentions FastMCP with DCR

**Target State (v1.6.0):**
- RemoteAuthProvider with JWTVerifier for Supabase DCR
- Retain ChainedAuthProvider for optional API key fallback
- ~220 lines in auth.py (minor increase for proper DCR setup)

---

## Architecture Comparison

### Current (v1.5.0) - SupabaseProvider
```
MCP Client → IQ-MCP Server (SupabaseProvider) → Validates JWT
                ↓
         No DCR - manual client registration required
         Client must know auth flow details in advance
```

**Limitations:**
- No OAuth discovery metadata endpoint
- No dynamic client registration
- Clients need pre-configured OAuth details
- Not fully MCP-compliant for auth

### Target (v1.6.0) - RemoteAuthProvider
```
MCP Client ← Discovery Metadata ← IQ-MCP (RemoteAuthProvider + JWTVerifier)
    ↓                                      ↓
Self-registers via DCR              Validates JWTs via JWKS
    ↓                                      ↓
Supabase Auth (authorize + token) → IQ-MCP validates access token
```

**Benefits:**
- Full OAuth 2.1 resource server capabilities
- MCP clients auto-discover and register
- Standards-compliant authentication flow
- Same JWT validation as before (JWTVerifier)

---

## Critical Understanding: DCR Workflow

### What DCR Enables
When a user adds IQ-MCP to Claude Desktop:

1. **Discovery (automatic)**
   ```
   Claude → https://mcp.casimir.ai/iq/.well-known/oauth-protected-resource
   Gets: authorization_servers, scopes, jwks_uri
   ```

2. **Client Registration (automatic)**
   ```
   Claude → Supabase DCR endpoint
   Registers: client_id, redirect_uris
   Gets: client_id (no client_secret for public clients)
   ```

3. **User Authorization (interactive)**
   ```
   Claude → Supabase authorization endpoint
   User → Approves access
   Supabase → Issues authorization code
   ```

4. **Token Exchange (automatic)**
   ```
   Claude → Supabase token endpoint (with PKCE)
   Gets: access_token, refresh_token
   ```

5. **Authenticated Requests**
   ```
   Claude → IQ-MCP with Bearer token
   IQ-MCP → Validates JWT via JWKS
   IQ-MCP → Processes tool call
   ```

**Key Point**: RemoteAuthProvider exposes step 1 (discovery) which enables steps 2-5 to work automatically!

---

## Implementation Plan

### Phase 1: Verify Supabase Configuration (30 minutes)

**Using Supabase MCP Server:**

1. **Check DCR is enabled:**
   ```bash
   # Via Supabase MCP
   mcp__supabase__get_project { "id": "your-project-id" }
   ```

   **Expected:** OAuth Server section shows "Dynamic Client Registration: Enabled"

2. **Verify discovery endpoint:**
   ```bash
   curl https://your-project.supabase.co/.well-known/oauth-authorization-server/auth/v1
   ```

   **Expected:** Returns JSON with `registration_endpoint`, `authorization_endpoint`, etc.

3. **Check signing algorithm:**
   - Should be **ES256** or **RS256** (asymmetric)
   - HS256 won't work for MCP (symmetric keys can't be publicly shared)

**Deliverable:** Confirmation that Supabase project is DCR-ready

---

### Phase 2: Update Code (2 hours)

#### Step 2.1: Update `settings.py` (SupabaseAuthConfig)

**File:** `src/mcp_knowledge_graph/settings.py` (lines 289-349)

**Changes:**

```python
class SupabaseAuthConfig:
    """Supabase OAuth 2.1 authentication configuration with DCR support."""

    def __init__(
        self,
        *,
        enabled: bool,
        project_url: str | None,
        algorithm: Literal["RS256", "ES256"],  # Removed HS256 - DCR requires asymmetric
        required_scopes: list[str] | None = None,
        # New fields for RemoteAuthProvider
        authorization_servers: list[str] | None = None,
        allowed_client_redirect_uris: list[str] | None = None,
    ) -> None:
        self.enabled = bool(enabled)
        self.project_url = project_url
        self.algorithm = algorithm
        self.required_scopes = required_scopes or []

        # Default authorization_servers to Supabase auth endpoint
        if authorization_servers is None and project_url:
            self.authorization_servers = [f"{project_url.rstrip('/')}/auth/v1"]
        else:
            self.authorization_servers = authorization_servers or []

        # Optional redirect URI restrictions (defaults to localhost + https)
        self.allowed_client_redirect_uris = allowed_client_redirect_uris

    @classmethod
    def load(cls) -> "SupabaseAuthConfig | None":
        """Load Supabase OAuth configuration from environment variables."""
        enabled = os.getenv("IQ_ENABLE_SUPABASE_AUTH", "false").lower() == "true"

        if not enabled:
            return None

        project_url = os.getenv("IQ_SUPABASE_AUTH_PROJECT_URL")
        algorithm = os.getenv("IQ_SUPABASE_AUTH_ALGORITHM", "ES256")

        # Load new DCR-related variables
        auth_servers = os.getenv("IQ_OAUTH_AUTHORIZATION_SERVERS")
        allowed_uris = os.getenv("IQ_ALLOWED_CLIENT_REDIRECT_URIS")

        # Parse comma-separated lists
        authorization_servers = auth_servers.split(",") if auth_servers else None
        allowed_redirect_uris = allowed_uris.split(",") if allowed_uris else None

        # Validate algorithm (only asymmetric for DCR)
        if algorithm not in ["RS256", "ES256"]:
            logger.error(f"Invalid algorithm '{algorithm}' for DCR. Must be RS256 or ES256.")
            return None

        return cls(
            enabled=enabled,
            project_url=project_url,
            algorithm=algorithm,
            authorization_servers=authorization_servers,
            allowed_client_redirect_uris=allowed_redirect_uris,
        )

    def is_valid(self) -> bool:
        """Check if Supabase auth config is valid for DCR."""
        if not self.enabled:
            return False
        return bool(
            self.project_url
            and self.authorization_servers
            and self.algorithm in ["RS256", "ES256"]
        )
```

**Environment Variables (New):**
- `IQ_OAUTH_AUTHORIZATION_SERVERS` - Comma-separated list (optional, defaults to project_url/auth/v1)
- `IQ_ALLOWED_CLIENT_REDIRECT_URIS` - Comma-separated patterns (optional, defaults to localhost + https)

**Removed:**
- `jwt_secret` field (not needed for asymmetric)
- HS256 support (incompatible with DCR)

---

#### Step 2.2: Update `auth.py` (RemoteAuthProvider)

**File:** `src/mcp_knowledge_graph/auth.py` (lines 146-176)

**Replace:**
```python
# OLD: SupabaseProvider initialization (lines 146-176)
from fastmcp.server.auth.providers.supabase import SupabaseProvider

supabase_provider = SupabaseProvider(
    project_url=project_url,
    base_url=base_url,
    algorithm=supabase_auth.algorithm,
    required_scopes=supabase_auth.required_scopes or None,
)
```

**With:**
```python
# NEW: RemoteAuthProvider with JWTVerifier
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

project_url = supabase_auth.project_url.rstrip("/")
base_url = os.getenv("IQ_BASE_URL")

if not base_url:
    logger.error("❌ IQ_BASE_URL required for Supabase OAuth. Skipping Supabase auth.")
else:
    # JWT verifier for token validation (same as SupabaseProvider internally used)
    token_verifier = JWTVerifier(
        jwks_uri=f"{project_url}/auth/v1/.well-known/jwks.json",
        issuer=f"{project_url}/auth/v1",
        audience=base_url,  # IQ-MCP server is the audience
        required_scopes=supabase_auth.required_scopes or None,
    )

    # RemoteAuthProvider for DCR support
    remote_auth = RemoteAuthProvider(
        token_verifier=token_verifier,
        authorization_servers=[
            AnyHttpUrl(server) for server in supabase_auth.authorization_servers
        ],
        base_url=base_url,
        allowed_client_redirect_uris=supabase_auth.allowed_client_redirect_uris,
    )

    providers.append(remote_auth)
    logger.info("🔐 RemoteAuthProvider enabled - OAuth 2.1 with DCR")
    logger.info(f"   Authorization servers: {supabase_auth.authorization_servers}")
    logger.info(f"   JWT algorithm: {supabase_auth.algorithm}")
    logger.info(f"   Discovery endpoint: {base_url}/.well-known/oauth-protected-resource")
    logger.info("   MCP clients can now self-register via DCR!")
```

**Key Changes:**
1. **JWTVerifier** replaces SupabaseProvider's internal validation
2. **RemoteAuthProvider** wraps JWTVerifier and adds DCR metadata endpoints
3. **Same security**: JWT validation logic is identical (JWKS, issuer, audience)
4. **New capability**: Exposes `/.well-known/oauth-protected-resource` for MCP clients

**Lines changed:** ~80 lines (import changes + new provider setup)

---

#### Step 2.3: Update `.env.example`

**File:** `.env.example`

**Remove:**
```bash
# Removed (no longer needed for DCR)
# IQ_SUPABASE_JWT_SECRET=your-jwt-secret-here
```

**Add:**
```bash
# OAuth 2.1 Dynamic Client Registration (DCR)
# Authorization servers (comma-separated, optional - defaults to project_url/auth/v1)
IQ_OAUTH_AUTHORIZATION_SERVERS=https://your-project.supabase.co/auth/v1

# Allowed client redirect URIs (comma-separated patterns, optional)
# If not set, defaults to localhost and https:// URLs only
# IQ_ALLOWED_CLIENT_REDIRECT_URIS=http://localhost:*,https://*
```

**Update documentation:**
```bash
# Supabase Auth (OAuth 2.1 with DCR)
IQ_ENABLE_SUPABASE_AUTH=true
IQ_SUPABASE_AUTH_PROJECT_URL=https://your-project.supabase.co
IQ_SUPABASE_AUTH_ALGORITHM=ES256  # Must be ES256 or RS256 for DCR
IQ_BASE_URL=https://mcp.casimir.ai  # Required for OAuth audience validation
```

---

### Phase 3: Update Tests (1 hour)

**File:** `tests/test_auth.py`

**Add new test:**

```python
@pytest.mark.asyncio
async def test_remote_auth_provider_with_chained():
    """Test RemoteAuthProvider works in ChainedAuthProvider."""
    from fastmcp.server.auth import RemoteAuthProvider
    from fastmcp.server.auth.providers.jwt import JWTVerifier, StaticTokenVerifier
    from mcp_knowledge_graph.auth import ChainedAuthProvider

    # Mock JWT verifier (would validate real JWTs in production)
    jwt_verifier = JWTVerifier(
        jwks_uri="https://example.supabase.co/auth/v1/.well-known/jwks.json",
        issuer="https://example.supabase.co/auth/v1",
        audience="https://mcp.example.com",
    )

    # RemoteAuthProvider with DCR
    remote_provider = RemoteAuthProvider(
        token_verifier=jwt_verifier,
        authorization_servers=["https://example.supabase.co/auth/v1"],
        base_url="https://mcp.example.com",
    )

    # API key fallback
    api_provider = StaticTokenVerifier(
        tokens={"test-key": {"client_id": "test", "scopes": ["read"]}},
        required_scopes=["read"],
    )

    # Chain providers
    chained = ChainedAuthProvider([remote_provider, api_provider])

    # API key should work
    result = await chained.verify_token("test-key")
    assert result is not None
    assert result.client_id == "test"

    # Check routes include OAuth discovery
    routes = chained.get_routes("/mcp")
    route_paths = [r.path for r in routes]
    assert "/.well-known/oauth-protected-resource/mcp" in route_paths
```

**Expected test count:** 24 tests (21 existing + 3 new RemoteAuthProvider tests)

---

### Phase 4: Update Documentation (30 minutes)

#### docs/SECURITY.md

**Add new section:**

```markdown
### OAuth 2.1 with Dynamic Client Registration

IQ-MCP supports OAuth 2.1 authentication via Supabase Auth with Dynamic Client Registration (DCR). This enables MCP clients like Claude Desktop to automatically discover and register without manual configuration.

#### How DCR Works

1. **Discovery**: MCP client fetches `/.well-known/oauth-protected-resource` from IQ-MCP
2. **Registration**: Client registers itself with Supabase's DCR endpoint
3. **Authorization**: User approves access via Supabase's OAuth flow
4. **Token Usage**: Client uses access token to call IQ-MCP tools

#### Setup Requirements

**Supabase Project:**
- OAuth 2.1 Server enabled
- Dynamic Client Registration enabled (Authentication > OAuth Server)
- JWT signing algorithm: **ES256** or **RS256** (asymmetric keys required)

**IQ-MCP Server:**
```bash
IQ_ENABLE_SUPABASE_AUTH=true
IQ_SUPABASE_AUTH_PROJECT_URL=https://your-project.supabase.co
IQ_SUPABASE_AUTH_ALGORITHM=ES256
IQ_BASE_URL=https://mcp.casimir.ai
```

#### Security Considerations

- **User approval required**: Each client registration requires user consent via Supabase
- **Redirect URI validation**: Supabase validates all redirect URIs during registration
- **Token validation**: IQ-MCP validates JWT signature, issuer, audience, expiration
- **RLS policies**: Supabase RLS policies apply to OAuth tokens based on `client_id`

#### Testing DCR

Use the MCP Inspector to test the OAuth flow:

```bash
npx @modelcontextprotocol/inspector --cli https://mcp.casimir.ai/iq \
  --transport http \
  --method tools/list
# Should trigger OAuth discovery + DCR flow
```
```

#### AGENTS.md

**Update provider table:**

| Provider | Use Case | DCR Support | Docs |
|----------|----------|-------------|------|
| `RemoteAuthProvider` | OAuth 2.1 with DCR (Supabase, any OIDC provider) | ✅ Yes | [docs](https://gofastmcp.com/servers/auth/remote-oauth) |
| `SupabaseProvider` | Supabase Auth (JWT-only, no DCR) | ❌ No | [docs](https://gofastmcp.com/python-sdk/fastmcp-server-auth-providers-supabase) |
| `OAuthProxy` | OAuth without DCR (legacy) | ❌ No | [docs](https://gofastmcp.com/servers/auth/oauth-proxy) |
| `GitHubProvider` | GitHub OAuth | ✅ Yes | Built-in |
| `StaticTokenVerifier` | API key auth | N/A | Built-in |

**Current Implementation (v1.6.0):**
- Uses **RemoteAuthProvider** with JWTVerifier for Supabase DCR
- MCP clients auto-discover and register via DCR
- Dual auth: OAuth 2.1 (primary) + API keys (fallback)
- See `src/mcp_knowledge_graph/auth.py`

---

### Phase 5: Environment Configuration (15 minutes)

**Update production `.env` on Railway:**

Using Railway MCP:

```bash
# Remove deprecated variables
railway variables delete IQ_SUPABASE_JWT_SECRET --environment production

# Add new variables
railway variables set \
  IQ_OAUTH_AUTHORIZATION_SERVERS="https://your-project.supabase.co/auth/v1" \
  --environment production

# Verify algorithm is asymmetric
railway variables get IQ_SUPABASE_AUTH_ALGORITHM --environment production
# Should be ES256 or RS256
```

**Or manually update in Railway dashboard:**

1. Navigate to project > Variables
2. Remove: `IQ_SUPABASE_JWT_SECRET`
3. Add: `IQ_OAUTH_AUTHORIZATION_SERVERS` = `https://your-project.supabase.co/auth/v1`
4. Verify: `IQ_SUPABASE_AUTH_ALGORITHM` = `ES256`

---

## Testing Strategy

### Local Testing (Before Deployment)

1. **Unit Tests:**
   ```bash
   pytest tests/test_auth.py -v
   # Expected: 24 tests pass
   ```

2. **Start Local Server:**
   ```bash
   # Activate venv first
   .venv/Scripts/Activate.ps1

   # Run locally
   IQ_TRANSPORT=http \
   IQ_ENABLE_SUPABASE_AUTH=true \
   IQ_SUPABASE_AUTH_PROJECT_URL=https://your-project.supabase.co \
   IQ_BASE_URL=http://localhost:8000 \
   python -m mcp_knowledge_graph
   ```

3. **Check Discovery Endpoint:**
   ```bash
   curl http://localhost:8000/.well-known/oauth-protected-resource

   # Expected response:
   {
     "resource": "http://localhost:8000",
     "authorization_servers": ["https://your-project.supabase.co/auth/v1"],
     "jwks_uri": "https://your-project.supabase.co/auth/v1/.well-known/jwks.json",
     "scopes_supported": ["read", "write"]
   }
   ```

4. **Test with MCP Inspector:**
   ```bash
   npx @modelcontextprotocol/inspector --cli http://localhost:8000 \
     --transport http \
     --method tools/list

   # Should trigger OAuth flow in browser
   ```

### Production Testing (After Deployment)

1. **Health Check:**
   ```bash
   curl https://mcp.casimir.ai/iq/.well-known/oauth-protected-resource
   # Should return OAuth metadata
   ```

2. **Claude Desktop Integration:**
   - Add IQ-MCP server in Claude Desktop settings
   - Should auto-discover OAuth configuration
   - Should trigger Supabase authorization flow
   - Should successfully call tools after auth

3. **API Key Fallback:**
   ```bash
   npx @modelcontextprotocol/inspector --cli https://mcp.casimir.ai/iq \
     --transport http \
     --header "Authorization: Bearer YOUR_API_KEY" \
     --method tools/list

   # Should work without OAuth flow
   ```

---

## Deployment Strategy

### Pre-Deployment Checklist

- [ ] All unit tests pass locally
- [ ] Discovery endpoint returns valid OAuth metadata
- [ ] MCP Inspector can trigger OAuth flow locally
- [ ] Supabase project has DCR enabled
- [ ] Supabase JWT algorithm is ES256 or RS256
- [ ] Railway environment variables updated

### Deployment Steps (Using Railway MCP)

1. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: implement OAuth 2.1 with RemoteAuthProvider for DCR support"
   git push origin main
   ```

2. **Monitor deployment:**
   ```bash
   # Railway auto-deploys on push to main
   railway logs --environment production --follow
   ```

3. **Verify deployment:**
   ```bash
   # Check discovery endpoint
   curl https://mcp.casimir.ai/iq/.well-known/oauth-protected-resource

   # Test with MCP Inspector
   npx @modelcontextprotocol/inspector --cli https://mcp.casimir.ai/iq \
     --transport http \
     --method tools/list
   ```

### Rollback Plan

If OAuth discovery fails or MCP clients can't register:

1. **Revert git commit:**
   ```bash
   git revert HEAD
   git push origin main
   ```

2. **Railway auto-deploys reverted version** (~2 minutes)

3. **Verify rollback:**
   ```bash
   # API key auth should still work
   curl https://mcp.casimir.ai/iq \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"method": "tools/list"}'
   ```

---

## Success Criteria

### Functional Requirements
- [ ] Discovery endpoint returns valid OAuth metadata
- [ ] MCP Inspector can complete OAuth flow
- [ ] Claude Desktop can auto-register and authenticate
- [ ] API key authentication still works (fallback)
- [ ] All existing tools work with OAuth tokens
- [ ] JWT validation time < 100ms

### Documentation Requirements
- [ ] SECURITY.md updated with DCR setup
- [ ] AGENTS.md updated with provider comparison
- [ ] .env.example has correct variables
- [ ] Migration guide created

### Testing Requirements
- [ ] 24+ unit tests pass
- [ ] OAuth flow works with MCP Inspector
- [ ] Claude Desktop integration verified
- [ ] API key fallback tested
- [ ] Performance benchmarks met

---

## Risk Mitigation

### Risk: OAuth discovery endpoint not accessible

**Impact:** MCP clients can't discover auth configuration

**Mitigation:**
- Test discovery endpoint thoroughly before deployment
- Verify FastMCP's RemoteAuthProvider route registration
- Check nginx reverse proxy doesn't block `/.well-known/` paths

**Detection:** `curl https://mcp.casimir.ai/iq/.well-known/oauth-protected-resource` returns 404

### Risk: Supabase DCR not enabled

**Impact:** Clients can't register themselves

**Mitigation:**
- Verify DCR enabled in Supabase dashboard before deployment
- Test registration with MCP Inspector locally first
- Document DCR setup in SECURITY.md

**Detection:** MCP Inspector shows "Registration failed: 403"

### Risk: JWT validation fails

**Impact:** Valid OAuth tokens rejected

**Mitigation:**
- Use same JWTVerifier logic as SupabaseProvider
- Verify JWKS URI accessible from IQ-MCP server
- Test token validation with real Supabase tokens

**Detection:** Server logs show "JWT verification failed" for valid tokens

### Risk: API key fallback breaks

**Impact:** Existing clients can't authenticate

**Mitigation:**
- ChainedAuthProvider tries API keys first (faster)
- Test API key auth after RemoteAuthProvider changes
- Keep StaticTokenVerifier unchanged

**Detection:** API key requests return 401

---

## Timeline Estimate

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Phase 1: Supabase Verification** | 30 min | Check DCR enabled, verify discovery endpoint, confirm algorithm |
| **Phase 2: Code Updates** | 2 hours | Update settings.py, auth.py, .env.example |
| **Phase 3: Tests** | 1 hour | Add RemoteAuthProvider tests, verify all pass |
| **Phase 4: Documentation** | 30 min | Update SECURITY.md, AGENTS.md, README.md |
| **Phase 5: Environment Config** | 15 min | Update Railway variables |
| **Phase 6: Local Testing** | 1 hour | Unit tests, MCP Inspector, discovery endpoint |
| **Phase 7: Deployment** | 30 min | Push to Railway, monitor deployment, verify |
| **Phase 8: Production Verification** | 1 hour | Test Claude Desktop, API keys, tools |
| **Total** | **6-7 hours** | |

---

## References

### FastMCP Documentation
- [RemoteAuthProvider](https://gofastmcp.com/servers/auth/remote-oauth)
- [SupabaseProvider](https://gofastmcp.com/python-sdk/fastmcp-server-auth-providers-supabase)
- [Authentication Overview](https://gofastmcp.com/servers/auth/authentication)

### Supabase Documentation
- [OAuth 2.1 Server](https://supabase.com/docs/guides/auth/oauth-server)
- [MCP Authentication](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication)
- [Getting Started with OAuth 2.1](https://supabase.com/docs/guides/auth/oauth-server/getting-started)
- [Dynamic Client Registration](https://github.com/orgs/supabase/discussions/38022)

### MCP Specification
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [OAuth 2.1 for MCP](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization)
- [Dynamic Client Registration](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization#dynamic-client-registration)

---

## Next Steps

1. **Review this revised plan** with the user
2. **Verify Supabase project** has DCR enabled
3. **Start Phase 2** (code updates) once approved
4. **Test locally** before deploying to Railway
5. **Deploy and verify** in production

**Questions to clarify:**
1. Is DCR already enabled in your Supabase project?
2. What's the current JWT signing algorithm? (Should be ES256/RS256)
3. Do you want to test locally first or deploy directly after code review?
