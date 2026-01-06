# Agent Scratchpad

## Current State (Dec 19, 2025)

**IQ-MCP v1.4.1 is ready for deployment!**

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

### Recent Changes (Dec 19, 2025) - v1.4.1
- **CLI Version Flag**: Added `--version` / `-v` flag to print version
- **Version Consistency**: Fixed version mismatch across all files (version.py, pyproject.toml, README.md, CHANGELOG.md)

### Previous Changes (v1.4.0)
- **Enhanced Entity References**: All CRUD tools now support ID or name/alias
- **Enhanced `update_user_info`**: Added optional `observations` parameter
- **Enhanced `read_graph`**: Added project awareness placeholder (ready for v1.5.0)
- Added `_resolve_entity_identifier()` helper for consistent entity resolution
- Added model validators to ensure proper identifier usage
- Added 10 new tests, all 21 tests passing

### Previous Changes (v1.3.1)
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

### Testing with MCP Inspector CLI

**Primary testing method:** Use `npx @modelcontextprotocol/inspector --cli` for all MCP server testing.

**List available tools:**
```bash
npx @modelcontextprotocol/inspector --cli https://iq-mcp-production.up.railway.app/iq \
  --transport http \
  --header "Authorization: Bearer YOUR_API_KEY" \
  --method tools/list
```

**Call a specific tool:**
```bash
npx @modelcontextprotocol/inspector --cli https://iq-mcp-production.up.railway.app/iq \
  --transport http \
  --header "Authorization: Bearer YOUR_API_KEY" \
  --method tools/call \
  --tool-name read_graph
```

**Call a tool with arguments:**
```bash
npx @modelcontextprotocol/inspector --cli https://iq-mcp-production.up.railway.app/iq \
  --transport http \
  --header "Authorization: Bearer YOUR_API_KEY" \
  --method tools/call \
  --tool-name search_nodes \
  --tool-arg query="test"
```

**Pass JSON arguments:**
```bash
npx @modelcontextprotocol/inspector --cli https://iq-mcp-production.up.railway.app/iq \
  --transport http \
  --header "Authorization: Bearer YOUR_API_KEY" \
  --method tools/call \
  --tool-name create_entities \
  --tool-arg 'new_entities=[{"name": "Test", "entity_type": "test"}]'
```

**Other useful methods:**
- `--method resources/list` - List available resources
- `--method prompts/list` - List available prompts

See: https://github.com/modelcontextprotocol/inspector

### Next Steps / Ideas
- Set up CI/CD for automatic deploys
- Add monitoring/alerting
- Consider backup strategy for memory.jsonl

