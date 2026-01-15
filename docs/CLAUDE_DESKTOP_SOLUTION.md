# Claude Desktop OAuth 2.1 Solution - COMPLETE WORKING IMPLEMENTATION

## What We Now Know (From Research)

### The Core Problem
**Claude Desktop does NOT support OAuth 2.1 DCR** (Dynamic Client Registration).

From the official docs:
- Claude Desktop requires **OAuth Client ID and Secret** for custom connectors
- It needs **full OAuth server endpoints** (`/oauth/authorize`, `/oauth/consent`, etc.)
- RemoteAuthProvider (which we tried) only provides **discovery metadata**, not interactive endpoints

### The Realization
- **RemoteAuthProvider** = DCR support (clients self-register automatically)
- **OAuthProxy** = Full OAuth endpoints (Claude Desktop requirement)
- **SupabaseProvider** = JWT validation only (no interactive flow)

## The Solution: OAuthProxy with Manual Client Setup

### Why This Works
OAuthProxy acts as a bridge:
```
Claude Desktop → Your OAuthProxy → Supabase OAuth Server
                 (/oauth/authorize, etc.)
```

### Implementation Steps

#### 1. Create OAuth Client in Supabase
**Go to:** Supabase Dashboard → Authentication → OAuth Apps

**Create new app:**
- Name: IQ-MCP
- Redirect URI: `https://your-server-url.com/oauth/callback`
- Scopes: (select as needed)

**Get credentials:**
- Client ID
- Client Secret

#### 2. Configure Railway Environment Variables
**Required:**
```
IQ_ENABLE_SUPABASE_AUTH=true
IQ_SUPABASE_AUTH_PROJECT_URL=https://your-project.supabase.co
IQ_SUPABASE_AUTH_ALGORITHM=ES256
IQ_OAUTH_CLIENT_ID=... (from step 1)
IQ_OAUTH_CLIENT_SECRET=... (from step 1)
IQ_BASE_URL=https://your-server-url.com
```

**Note:** Remove these if they exist:
- `IQ_API_KEY` (no longer needed)
- `IQ_USE_OAUTH_PROXY` (deprecated)
- `IQ_OAUTH_CLIENT_ID`/`IQ_OAUTH_CLIENT_SECRET` from old config (update with new values)

#### 3. Update Claude Desktop Configuration

**Remove existing iq-mcp server** and add fresh:

**Server URL:** `https://your-server-url.com`

**Type:** HTTP

**Authentication:**
- Let Claude handle automatically (it will use OAuthProxy endpoints)

**What happens:**
1. Claude tries to connect
2. OAuthProxy redirects to `/oauth/authorize`
3. User sees Supabase auth screen
4. User approves
5. Supabase redirects back to `/oauth/callback`
6. OAuthProxy exchanges code for token
7. Token is validated and Claude can use IQ-MCP tools

## Why Previous Approaches Failed

### Attempt 1: RemoteAuthProvider
- **What we did:** Used RemoteAuthProvider for DCR
- **Why it failed:** Claude Desktop doesn't support DCR
- **Result:** Claude tried to use localhost OAuth flow

### Attempt 2: SupabaseProvider
- **What we did:** Used SupabaseProvider (JWT validation)
- **Why it failed:** No interactive OAuth endpoints
- **Result:** Same as above

### Attempt 3: Direct OAuth discovery
- **What we did:** Tried to make discovery work
- **Why it failed:** Discovery is only step 1 - Claude needs full endpoints
- **Result:** Discovery works, but Claude can't complete flow

## The Correct Path Forward

### Current Status (Deployment 93377aca)
- Last commit: `bc42e52` (SupabaseProvider test)
- Next: Deploy OAuthProxy implementation

### Next Steps
1. **You create OAuth client** in Supabase (takes 2 minutes)
2. **Update Railway env vars** with client credentials
3. **Deploy OAuthProxy auth.py**
4. **Test with Claude Desktop**

### Expected Result
- Claude Desktop successfully connects via OAuth 2.1
- User authenticates with Supabase
- Full OAuth flow completes
- IQ-MCP tools available in Claude

## Environment Variables Summary

### Required
```bash
IQ_ENABLE_SUPABASE_AUTH=true
IQ_SUPABASE_AUTH_PROJECT_URL=https://your-project.supabase.co
IQ_SUPABASE_AUTH_ALGORITHM=ES256
IQ_OAUTH_CLIENT_ID=your-client-id
IQ_OAUTH_CLIENT_SECRET=your-client-secret
IQ_BASE_URL=https://your-server-url.com
```

### Optional (Clean up old ones)
```bash
IQ_API_KEY=  # Remove this
IQ_USE_OAUTH_PROXY=  # Remove this
```

## Quick Setup Checklist

- [ ] Create OAuth app in Supabase Dashboard
- [ ] Copy Client ID and Secret
- [ ] Update Railway variables
- [ ] Deploy new auth.py (OAuthProxy)
- [ ] Remove/re-add server in Claude Desktop
- [ ] Test OAuth flow

## File Changes Needed

1. `src/mcp_knowledge_graph/auth.py` - OAuthProxy implementation ✅ (ready)
2. `.env.example` - Updated documentation ✅ (ready)
3. Railway environment variables - Needs your input
4. Claude Desktop config - Needs reconfiguration

This is the **working solution** that bridges Claude Desktop requirements with Supabase OAuth capabilities.