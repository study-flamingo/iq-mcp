# OAuth 2.1 with RemoteAuthProvider Implementation Plan

## Executive Summary

**Goal:** Replace current ChainedAuthProvider pattern (using OAuthProxy/SupabaseProvider) with FastMCP's **RemoteAuthProvider** to enable proper OAuth 2.1 with Dynamic Client Registration (DCR) for Claude Desktop.

**Why RemoteAuthProvider?**
- Supabase supports DCR as of Nov 2025 (OAuth 2.1 Server feature)
- MCP clients like Claude Desktop can self-register automatically
- Simpler configuration (no manual client credentials needed)
- Better follows FastMCP best practices for modern OAuth providers

**Current State (v1.5.0):**
- Uses OAuthProxy (requires manual client ID/secret) OR SupabaseProvider (JWT-only)
- ChainedAuthProvider wrapper for dual auth (OAuth + API keys)
- ~268 lines in auth.py

**Target State (v1.6.0):**
- RemoteAuthProvider with JWTVerifier for Supabase DCR
- Retain ChainedAuthProvider for optional API key fallback
- ~200 lines in auth.py (25% reduction)

## Architecture

### Before (v1.5.0)
```
MCP Client → IQ-MCP Server (OAuthProxy) → Supabase Auth
                ↓
         Manual client registration required
         Server proxies OAuth flow
```

### After (v1.6.0)
```
MCP Client ← Supabase OAuth metadata ← IQ-MCP (RemoteAuthProvider)
    ↓                                           ↓
Self-registers via DCR               Validates JWTs via JWKS
    ↓
Supabase Auth (authorize + token)
```

## Implementation Steps

### Step 1: Update SupabaseAuthConfig (settings.py)

**File:** `src/mcp_knowledge_graph/settings.py` (lines 289-378)

**Remove these fields:**
- `client_id`, `client_secret`, `use_oauth_proxy` (no longer needed for DCR)

**Add these fields:**
- `authorization_servers: list[str]` - List of OAuth 2.1 authorization servers
- `allowed_redirect_uris: list[str] | None` - Patterns for DCR clients (optional)

**Update environment variable loading:**
```python
# New env vars for RemoteAuthProvider
IQ_OAUTH_AUTHORIZATION_SERVERS  # Default: {project_url}/auth/v1
IQ_ALLOWED_CLIENT_REDIRECT_URIS # Default: None (localhost only)
```

**Lines to modify:** ~90 lines

---

### Step 2: Replace OAuthProxy with RemoteAuthProvider (auth.py)

**File:** `src/mcp_knowledge_graph/auth.py` (lines 196-240)

**Remove:**
- OAuthProxy initialization (lines 196-224)
- SupabaseProvider fallback (lines 226-240)

**Replace with:**
```python
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.jwt import JWTVerifier
from pydantic import AnyHttpUrl

# JWT verifier for token validation
token_verifier = JWTVerifier(
    jwks_uri=f"{project_url}/auth/v1/.well-known/jwks.json",
    issuer=f"{project_url}/auth/v1",
    audience=auth_base_url,
)

# RemoteAuthProvider for DCR
remote_auth = RemoteAuthProvider(
    token_verifier=token_verifier,
    authorization_servers=[AnyHttpUrl(server) for server in supabase_auth.authorization_servers],
    base_url=auth_base_url,
    allowed_client_redirect_uris=supabase_auth.allowed_redirect_uris,
)

providers.append(remote_auth)
logger.info("🔐 RemoteAuthProvider enabled - OAuth 2.1 with DCR")
```

**Lines to modify:** ~80 lines changed, ~68 lines removed

---

### Step 3: Update Environment Variables (.env.example)

**File:** `.env.example` (lines 18-40)

**Remove these deprecated variables:**
```bash
IQ_USE_OAUTH_PROXY           # No longer needed
IQ_OAUTH_CLIENT_ID           # DCR handles registration
IQ_OAUTH_CLIENT_SECRET       # No pre-registered clients
```

**Add these new variables:**
```bash
# OAuth 2.1 Dynamic Client Registration (DCR)
IQ_OAUTH_AUTHORIZATION_SERVERS=https://your-project.supabase.co/auth/v1
IQ_ALLOWED_CLIENT_REDIRECT_URIS=  # Optional: comma-separated patterns
```

**Keep these existing variables:**
```bash
IQ_ENABLE_SUPABASE_AUTH=true
IQ_SUPABASE_AUTH_PROJECT_URL=https://your-project.supabase.co
IQ_SUPABASE_AUTH_ALGORITHM=ES256
IQ_BASE_URL=https://mcp.casimir.ai
```

**Lines to modify:** ~10 lines

---

### Step 4: Update Tests (test_auth.py)

**File:** `tests/test_auth.py`

**Add new tests:**
1. `test_remote_auth_provider_in_chain()` - Verify RemoteAuthProvider works with ChainedAuthProvider
2. `test_remote_auth_provider_fallback()` - Test API key fallback when OAuth fails
3. `test_remote_auth_provider_invalid_token()` - Rejection of invalid tokens

**Update existing tests:**
- Replace OAuthProxy references with RemoteAuthProvider
- Keep ChainedAuthProvider tests (still used for API key fallback)

**Lines to add:** ~50 lines

---

### Step 5: Update Documentation

**Files to update:**

1. **docs/SECURITY.md** (OAuth section)
   - Remove OAuthProxy references
   - Add DCR setup instructions
   - Update environment variables

2. **docs/DEVELOPMENT.md** (Testing section)
   - Update OAuth testing workflow
   - Add RemoteAuthProvider testing with MCP Inspector

3. **AGENTS.md** (Current OAuth Setup section)
   - Remove outdated "Important Update"
   - Update provider table with RemoteAuthProvider

4. **README.md** (Authentication section)
   - Simplify OAuth setup instructions
   - Emphasize DCR benefits

**Create new file:**
- **docs/OAUTH_DCR_MIGRATION.md** - Migration guide for v1.5.0 → v1.6.0

---

## Configuration Changes

### Environment Variables (Production .env)

**Before (v1.5.0):**
```bash
IQ_ENABLE_SUPABASE_AUTH=true
IQ_SUPABASE_AUTH_PROJECT_URL=https://xyz.supabase.co
IQ_USE_OAUTH_PROXY=true
IQ_OAUTH_CLIENT_ID=abc123
IQ_OAUTH_CLIENT_SECRET=secret456
IQ_ALLOWED_REDIRECT_URIS=http://localhost:*/callback
```

**After (v1.6.0):**
```bash
IQ_ENABLE_SUPABASE_AUTH=true
IQ_SUPABASE_AUTH_PROJECT_URL=https://xyz.supabase.co
IQ_OAUTH_AUTHORIZATION_SERVERS=https://xyz.supabase.co/auth/v1
# IQ_ALLOWED_CLIENT_REDIRECT_URIS=  # Optional (defaults to localhost)
```

### Supabase Dashboard Setup

**Required:**
1. Navigate to: **Authentication > OAuth Server**
2. Toggle: **Enable Dynamic Client Registration**
3. (Optional) Configure allowed redirect URI patterns
4. Save settings

---

## Testing & Verification

### Pre-Deployment Testing

**Unit Tests:**
```bash
pytest tests/test_auth.py -v
# Expected: All tests pass (existing + 3 new tests)
```

**Integration Tests:**

1. **MCP Inspector (API Key):**
   ```bash
   npx @modelcontextprotocol/inspector --cli https://mcp.casimir.ai/iq \
     --transport http \
     --header "Authorization: Bearer YOUR_API_KEY" \
     --method tools/list
   ```

2. **MCP Inspector (OAuth):**
   ```bash
   npx @modelcontextprotocol/inspector --cli https://mcp.casimir.ai/iq \
     --transport http \
     --method tools/list
   # Should trigger OAuth flow with DCR
   ```

3. **Claude Desktop:**
   - Configure MCP server in Claude Desktop settings
   - Verify OAuth consent screen appears
   - Test that Claude can access IQ-MCP tools

### Post-Deployment Verification

**Health Checks:**
- [ ] Server starts without errors
- [ ] OAuth discovery endpoint responds: `/.well-known/oauth-protected-resource/iq`
- [ ] JWKS endpoint accessible from server
- [ ] ChainedAuthProvider tries RemoteAuthProvider first, API key second
- [ ] Token validation < 100ms (JWTVerifier performance)

**Monitoring:**
- Watch server logs for auth failures
- Check Supabase dashboard for DCR registrations
- Monitor token validation latency

---

## Deployment Strategy

### Phase 1: Pre-Deployment (Day 1)
1. Enable DCR in Supabase dashboard (production project)
2. Test DCR works with staging environment
3. Backup current production .env file
4. Build and push v1.6.0 Docker image to registry

### Phase 2: Deployment (Day 2)
1. Update production .env with new variables
2. Remove deprecated variables (client_id, client_secret, use_oauth_proxy)
3. Pull v1.6.0 Docker image: `./deploy/pull-and-deploy.sh`
4. Server restart: ~30 seconds downtime

### Phase 3: Verification (Day 2-3)
1. Test OAuth flow with test account + Claude Desktop
2. Verify API key fallback works
3. Monitor logs for auth errors
4. User acceptance testing

---

## Rollback Plan

### When to Rollback
- OAuth flow fails for >50% of clients
- JWTVerifier performance issues (>500ms validation)
- DCR registration failures in Supabase
- Critical auth bugs discovered

### How to Rollback
1. **Deploy previous image:**
   ```bash
   cd /opt/iq-mcp
   docker-compose pull iq-mcp:v1.5.0
   docker-compose up -d
   ```

2. **Restore .env:**
   ```bash
   cp .env.backup.v1.5.0 .env
   docker-compose restart
   ```

3. **Verify:**
   - Test OAuth flow with v1.5.0 (OAuthProxy)
   - Check server logs clear
   - Time to rollback: <5 minutes

---

## Critical Files

These are the 5 files that MUST be modified for this implementation:

1. **src/mcp_knowledge_graph/auth.py** - Core auth logic (80% of work)
2. **src/mcp_knowledge_graph/settings.py** - Config loading (15% of work)
3. **tests/test_auth.py** - Test coverage (quality assurance)
4. **.env.example** - Variable documentation (user onboarding)
5. **docs/SECURITY.md** - OAuth setup guide (operational success)

---

## Expected Outcomes

### Code Quality
- **Lines removed:** ~68 lines (OAuthProxy complexity eliminated)
- **Lines added:** ~270 lines (RemoteAuthProvider + tests + docs)
- **Net change:** +180 lines total
- **Complexity:** 25% reduction in auth.py

### Performance
- **Token validation:** <50ms (JWTVerifier with local JWKS cache)
- **OAuth discovery:** Cached by RemoteAuthProvider (no performance impact)
- **Expected improvement:** 30-50% reduction in auth latency vs OAuthProxy

### Security
- **No client secrets** in server configuration (DCR handles registration)
- **JWT validation** with signature, issuer, audience, expiration checks
- **JWKS auto-refresh** every 5 minutes (FastMCP default)
- **API key fallback** remains secure (existing StaticTokenVerifier)

### Developer Experience
- **Simpler config:** 3 env vars removed, 2 added (net: -1)
- **No manual client registration:** DCR automates this
- **Better FastMCP alignment:** Uses recommended provider for modern OAuth

---

## Sources

This plan is based on:
- [FastMCP RemoteAuthProvider Documentation](https://gofastmcp.com/servers/auth/remote-oauth)
- [Supabase OAuth 2.1 Server | Supabase Docs](https://supabase.com/docs/guides/auth/oauth-server)
- [Model Context Protocol (MCP) Authentication | Supabase Docs](https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication)
- [Getting Started with OAuth 2.1 Server | Supabase Docs](https://supabase.com/docs/guides/auth/oauth-server/getting-started)
- [OAuth 2.1 Server Capabilities Discussion](https://github.com/orgs/supabase/discussions/38022)
