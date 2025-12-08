# Agent Scratchpad

## Current State (Dec 7, 2025)

**IQ-MCP is deployed and live!**

### Production Deployment
- **Endpoint:** `https://mcp.casimir.ai/iq`
- **API Key:** `iqmcp-sk-qwA9sdZrWdunSPpvUBu9IYju9hbGXRcDOaSRQ0xT7MU`
- **VM:** `dted-ai-agent-vm` (GCP, `us-central1-c`, IP: `35.193.225.215`)
- **Auth:** `StaticTokenVerifier` (FastMCP 2.13.3)
- **Supabase:** Enabled (`ahsrjqkbdtgdlgpfewxz.supabase.co`)

### Architecture
```
Client → https://mcp.casimir.ai/iq
         ↓
      nginx (SSL termination, /iq → /mcp rewrite)
         ↓
      iq-mcp container (FastMCP on port 8000, stateless HTTP mode)
         ↓
      Supabase (cloud sync) + local JSONL
```

### Important: Stateless HTTP Mode
- `FASTMCP_STATELESS_HTTP=true` is required for Cursor compatibility
- Without this, clients get "No valid session ID" errors

### Key Files on VM (`/opt/iq-mcp/`)
- `.env` - API keys, Supabase config
- `docker-compose.yml` - orchestration
- `nginx/conf.d/mcp.conf` - reverse proxy config
- `nginx/ssl/` - Let's Encrypt certs (auto-renew via certbot)
- `data/` - persistent memory storage

### Local Development
- SSH config: `iq-mcp-vm` → connects to VM
- Deploy scripts in `deploy/`:
  - `deploy.sh` - full rebuild
  - `quick-deploy.sh` - source-only sync
  - `vm-logs.sh` - view container logs
  - `vm-ssh.sh` - SSH shortcut

### Recent Changes
- Upgraded FastMCP to 2.13.3 for auth support
- Added `StaticTokenVerifier` auth (`src/mcp_knowledge_graph/auth.py`)
- Moved `supabase` to main dependencies in `pyproject.toml`
- Created Docker + nginx deployment stack

### Cursor MCP Config (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "iq-mcp": {
      "type": "http",
      "url": "https://mcp.casimir.ai/iq",
      "headers": {
        "Authorization": "Bearer iqmcp-sk-qwA9sdZrWdunSPpvUBu9IYju9hbGXRcDOaSRQ0xT7MU"
      }
    }
  }
}
```

### Next Steps / Ideas
- Set up CI/CD for automatic deploys
- Add monitoring/alerting
- Consider backup strategy for memory.jsonl

