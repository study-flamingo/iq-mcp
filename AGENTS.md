# Agent Scratchpad

## Current State (Dec 19, 2025)

**IQ-MCP v1.3.1 is deployed and live!**

### Production Deployment
- **Endpoint:** `https://mcp.casimir.ai/iq`
- **API Key:** `iqmcp-sk-qwA9sdZrWdunSPpvUBu9IYju9hbGXRcDOaSRQ0xT7MU`
- **VM:** `dted-ai-agent-vm` (GCP, `us-central1-c`, IP: `35.193.225.215`)
- **Auth:** `StaticTokenVerifier` (FastMCP 2.13.3)
- **Supabase:** Enabled (`xxx.supabase.co`)

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

### Deployment Workflow (Registry-based)
Images are pushed to Google Artifact Registry and pulled on the VM:

```bash
# One-command deploy (build, push, pull, restart):
./deploy/push-and-deploy.sh

# Or step-by-step:
./deploy/push-image.sh        # Build & push to registry
ssh iq-mcp-vm 'cd /opt/iq-mcp && ./pull-and-deploy.sh'
```

**Registry:** `us-central1-docker.pkg.dev/dted-ai-agent/iq-mcp/iq-mcp`

### Local Development
- SSH config: `iq-mcp-vm` → connects to VM
- Deploy scripts in `deploy/`:
  - `push-and-deploy.sh` - full registry-based deploy (recommended)
  - `push-image.sh` - build & push to Artifact Registry
  - `pull-and-deploy.sh` - runs on VM to pull & restart
  - `deploy.sh` - legacy: scp + rebuild
  - `quick-deploy.sh` - legacy: source-only sync
  - `vm-logs.sh` - view container logs
  - `vm-ssh.sh` - SSH shortcut

### Recent Changes (Dec 19, 2025)
- Fixed `UpdateEntityRequest` model (fields were tuples)
- Fixed `update_entity` server function (identifier extraction)
- Fixed test fixture (AppSettings + logger)
- Fixed Supabase observations upsert (added missing UNIQUE constraint)
- Added registry-based deployment workflow (Artifact Registry)
- Improved timestamp serialization for Supabase (isoformat)

### Previous Changes
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

### Documentation
- `docs/DEVELOPMENT.md` - Complete development guide with deployment workflow
- `docs/PROJECT_OVERVIEW.md` - Architecture and module responsibilities
- `docs/WORKFLOWS.md` - Tool workflows and data flow
- `docs/SUPABASE_SCHEMA.md` - Supabase table schema

### Next Steps / Ideas
- Set up CI/CD for automatic deploys
- Add monitoring/alerting
- Consider backup strategy for memory.jsonl

