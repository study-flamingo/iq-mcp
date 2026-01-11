**Whenever working in this project, run `source .venv/scripts/activate`** to activate the correct environment!

After pushing to `dev` or `main` branches on github, the dev deployment server will restart automatically. It takes about 120 seconds to restart. Rate-limit accordingly.

## Current State (Jan 9, 2026)

**IQ-MCP v1.5.0 is ready for deployment!**

### Production Deployment
- **Endpoint:** `https://mcp.casimir.ai/iq`
- **API Key:** `[See .env file or deployment secrets - NEVER commit this!]`
- **VM:** `dted-ai-agent-vm` (GCP, `us-central1-c`)
- **Auth:** Dual auth - OAuth 2.1 (Supabase) + API keys (FastMCP 2.13.3+)
- **Supabase:** Enabled

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
In `scripts/`:
- `rotate-service-key.sh/ps1` - Generate a new service API key, and push to Railway with environment targeting (--prod/--dev/--all)

### Recent Changes (Jan 9, 2026) - v1.5.0
- **OAuth 2.1 Support**: Added Supabase Auth integration with JWT validation
- **Dual Authentication**: Supports both OAuth 2.1 and API key authentication simultaneously
- **Enhanced Security**: New security module with CORS configuration and rate limiting
- **Enhanced Key Rotation**: Scripts now support --prod/--dev/--all flags for environment targeting
- **Improved Key Display**: Redacted output shows first 12 and last 4 characters
- **Security Documentation**: Comprehensive security guide in docs/SECURITY.md (401 lines)
- **URL Auth Middleware**: Optional --url-auth flag for query parameter authentication
- **Railway Deployment Fixes**: Fixed url_auth AttributeError and stateless HTTP compatibility
- **Extended Testing**: Added 153 lines of auth tests, all passing

### Previous Changes (Dec 19, 2025) - v1.4.1
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
        "Authorization": "Bearer YOUR_API_KEY_HERE"
      }
    }
  }
}
```

**Note:** Replace `YOUR_API_KEY_HERE` with your actual API key from the production `.env` file.

### Documentation
- `docs/DEVELOPMENT.md` - Complete development guide with deployment workflow
- `docs/PROJECT_OVERVIEW.md` - Architecture and module responsibilities
- `docs/WORKFLOWS.md` - Tool workflows and data flow
- `docs/SUPABASE_SCHEMA.md` - Supabase table schema
- `docs/SECURITY.md` - Authentication, authorization, and security best practices
- `.my_deployment.md` - Deployment URLs and testing info (git-ignored, create your own copy)

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

