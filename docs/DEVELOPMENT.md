# Development Guide

This guide covers everything you need to know to develop, test, and deploy IQ-MCP.

## Table of Contents

- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Development Workflow](#development-workflow)
- [Deployment Workflow](#deployment-workflow)
- [Project Structure](#project-structure)
- [Debugging](#debugging)
- [Common Tasks](#common-tasks)
- [Contributing](#contributing)

## Development Setup

### Prerequisites

- **Python 3.13+** (required by `pyproject.toml`)
- **Docker** (for building and testing containers)
- **gcloud CLI** (for deployment to GCP)
- **Git** (for version control)

### Installation

```bash
# Clone the repository
git clone https://github.com/study-flamingo/mcp-server-memory-temporal.git
cd mcp-server-memory-temporal

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Or using uv (recommended)
uv sync
```

### Environment Variables

Copy `example.env` to `.env` and configure:

```bash
cp example.env .env
# Edit .env with your settings
```

Key variables for development:
- `IQ_MEMORY_PATH` - Path to your local memory.jsonl file
- `IQ_DEBUG=true` - Enable verbose logging
- `IQ_ENABLE_SUPABASE=false` - Disable Supabase for local testing (optional)

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=mcp_knowledge_graph --cov-report=html
```

### Run Specific Test File

```bash
pytest tests/test_graph.py -v
```

### Test Output

All 11 unit tests should pass:
- ✅ Entity creation (single, multiple, duplicates)
- ✅ Graph reading and searching
- ✅ Relation creation
- ✅ Observation operations (add, deduplication, cleanup)
- ✅ Entity alias resolution
- ✅ Persistence across sessions

## Development Workflow

### Making Changes

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Follow existing code style
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests:**
   ```bash
   pytest
   ```

4. **Check code quality:**
   ```bash
   ruff check src/ tests/
   ```

5. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat: description of changes"
   ```

### Code Style

- Follow PEP 8
- Use type hints
- Document public functions with docstrings
- Keep functions focused and small

### Version Bumping

When releasing a new version:

1. Update `pyproject.toml`:
   ```toml
   version = "1.3.2"
   ```

2. Update `src/mcp_knowledge_graph/version.py`:
   ```python
   IQ_MCP_VERSION: str = "1.3.2"
   ```

3. Update `CHANGELOG.md` with changes

4. Commit and tag:
   ```bash
   git commit -m "chore: bump version to 1.3.2"
   git tag v1.3.2
   ```

## Deployment Workflow

IQ-MCP uses **Google Artifact Registry** for containerized deployments. The workflow builds images locally, pushes to the registry, and pulls on the VM.

### Architecture

```
Local Dev → Build Image → Push to Artifact Registry → VM Pulls → Restart Containers
```

### One-Command Deploy

```bash
./deploy/push-and-deploy.sh
```

This script:
1. Builds the Docker image locally
2. Tags it with version and `latest`
3. Pushes to `us-central1-docker.pkg.dev/dted-ai-agent/iq-mcp/iq-mcp`
4. SSHs to VM using `gcloud compute ssh`
5. Pulls the new image
6. Restarts containers with `docker-compose.prod.yml`

### Manual Deployment Steps

If you need to deploy step-by-step:

```bash
# 1. Build and push image
./deploy/push-image.sh

# 2. Deploy on VM (runs pull-and-deploy.sh)
gcloud compute ssh dted-ai-agent-vm \
  --zone=us-central1-c \
  --project=dted-ai-agent \
  --command="cd /opt/iq-mcp && ./pull-and-deploy.sh"
```

### First-Time Setup

#### Local Machine

```bash
# Install gcloud CLI (if not installed)
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud config set project dted-ai-agent

# Configure Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Create Artifact Registry repository (one-time)
gcloud artifacts repositories create iq-mcp \
  --repository-format=docker \
  --location=us-central1 \
  --description="IQ-MCP Docker images"
```

#### On VM

```bash
# SSH to VM
gcloud compute ssh dted-ai-agent-vm --zone=us-central1-c --project=dted-ai-agent

# Configure Docker auth
gcloud auth configure-docker us-central1-docker.pkg.dev

# Copy required files (one-time, from local machine)
# From your local dev environment:
gcloud compute scp docker-compose.prod.yml deploy/pull-and-deploy.sh \
  dted-ai-agent-vm:/opt/iq-mcp/ \
  --zone=us-central1-c --project=dted-ai-agent

# Make deploy script executable
gcloud compute ssh dted-ai-agent-vm --zone=us-central1-c --project=dted-ai-agent \
  --command="chmod +x /opt/iq-mcp/pull-and-deploy.sh"
```

### Deploy Scripts Reference

| Script | Location | Purpose |
|--------|----------|---------|
| `push-and-deploy.sh` | `deploy/` | One-command full deployment |
| `push-image.sh` | `deploy/` | Build and push to Artifact Registry |
| `pull-and-deploy.sh` | VM: `/opt/iq-mcp/` | Pull image and restart containers |
| `deploy.sh` | `deploy/` | Legacy: scp + rebuild |
| `quick-deploy.sh` | `deploy/` | Legacy: source-only sync |

### Docker Compose Files

- **`docker-compose.yml`** - Local development (builds from source)
- **`docker-compose.prod.yml`** - Production (pulls from Artifact Registry)

### Troubleshooting Deployment

**Error: "Unauthenticated request"**
```bash
# Re-authenticate Docker
gcloud auth configure-docker us-central1-docker.pkg.dev
```

**Error: "SSH connection failed"**
```bash
# Test SSH connection
gcloud compute ssh dted-ai-agent-vm --zone=us-central1-c --project=dted-ai-agent

# Check VM status
gcloud compute instances list --project=dted-ai-agent
```

**Error: "Repository does not exist"**
```bash
# Create the repository
gcloud artifacts repositories create iq-mcp \
  --repository-format=docker \
  --location=us-central1 \
  --project=dted-ai-agent
```

**View VM logs:**
```bash
gcloud compute ssh dted-ai-agent-vm --zone=us-central1-c --project=dted-ai-agent \
  --command="cd /opt/iq-mcp && docker compose -f docker-compose.prod.yml logs --tail=50 iq-mcp"
```

## Project Structure

```
iq-mcp-dev/
├── src/
│   └── mcp_knowledge_graph/
│       ├── __init__.py
│       ├── __main__.py          # Entry point
│       ├── context.py            # AppContext singleton
│       ├── manager.py            # Business logic
│       ├── models.py             # Pydantic data models
│       ├── server.py             # MCP tools
│       ├── settings.py           # Configuration
│       ├── supabase_manager.py   # Supabase integration
│       ├── version.py            # Version constants
│       └── utils/
│           ├── migrate_graph.py
│           └── seed_graph.py
├── tests/
│   └── test_graph.py             # Unit tests
├── deploy/
│   ├── push-and-deploy.sh        # Full deployment
│   ├── push-image.sh             # Build & push
│   ├── pull-and-deploy.sh        # VM deploy script
│   └── ...
├── docs/
│   ├── DEVELOPMENT.md            # This file
│   ├── PROJECT_OVERVIEW.md       # Architecture
│   ├── WORKFLOWS.md              # Tool workflows
│   └── ...
├── Dockerfile                     # Container definition
├── docker-compose.yml             # Local dev compose
├── docker-compose.prod.yml        # Production compose
└── pyproject.toml                 # Package config
```

### Key Modules

- **`context.py`** - Runtime state (settings, logger, Supabase). Initialize with `ctx.init()`
- **`manager.py`** - All graph operations (CRUD, search, merge, cleanup)
- **`server.py`** - MCP tool endpoints that call manager methods
- **`models.py`** - Pydantic v2 models (Entity, Relation, Observation, etc.)

See `docs/PROJECT_OVERVIEW.md` for detailed architecture.

## Debugging

### Local Development

**Enable debug logging:**
```bash
IQ_DEBUG=true python -m mcp_knowledge_graph
```

**Run with verbose output:**
```bash
python -m mcp_knowledge_graph --debug --memory-path ./memory.jsonl
```

**Test MCP tools locally:**
```bash
# Start server
IQ_TRANSPORT=http IQ_STREAMABLE_HTTP_PORT=8000 python -m mcp_knowledge_graph

# In another terminal, test with curl
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}'
```

### Container Debugging

**View container logs:**
```bash
# Local
docker compose logs -f iq-mcp

# Production VM
gcloud compute ssh dted-ai-agent-vm --zone=us-central1-c --project=dted-ai-agent \
  --command="cd /opt/iq-mcp && docker compose -f docker-compose.prod.yml logs -f iq-mcp"
```

**Shell into container:**
```bash
docker compose exec iq-mcp /bin/bash
```

**Check container status:**
```bash
docker compose ps
```

### Common Issues

**"AppContext not initialized"**
- Ensure `ctx.init()` is called before accessing `ctx.settings` or `ctx.logger`
- Check that `__main__.py` calls `ctx.init()` at startup

**"Entity not found"**
- Check entity name/ID spelling
- Verify entity exists: `search_nodes("entity_name")`
- Check if entity was deleted or merged

**"Supabase sync failed"**
- Verify `IQ_ENABLE_SUPABASE=true` and credentials are set
- Check Supabase table constraints (see `docs/SUPABASE_SCHEMA.md`)
- Review Supabase logs in container output

## Common Tasks

### Add a New MCP Tool

1. **Add tool function in `server.py`:**
   ```python
   @mcp.tool
   async def my_new_tool(param: str):
       """Tool description."""
       # Use manager for business logic
       result = await manager.some_method(param)
       return format_result(result)
   ```

2. **Add manager method if needed:**
   ```python
   # In manager.py
   async def some_method(self, param: str) -> Result:
       graph = await self._load_graph()
       # ... business logic ...
       await self._save_graph(graph)
       return result
   ```

3. **Add tests:**
   ```python
   # In tests/test_graph.py
   @pytest.mark.asyncio
   async def test_my_new_tool(mock_context):
       # Test implementation
   ```

### Update Data Models

1. **Modify model in `models.py`:**
   ```python
   class MyModel(BaseModel):
       new_field: str = Field(...)
   ```

2. **Update schema version if breaking:**
   ```python
   # In version.py
   IQ_MCP_SCHEMA_VERSION = 2  # Increment if breaking change
   ```

3. **Add migration logic in `manager.py`** if needed:
   ```python
   async def _migrate_graph(self, graph: KnowledgeGraph) -> KnowledgeGraph:
       if graph.meta.schema_version < 2:
           # Migration logic
           graph.meta.schema_version = 2
       return graph
   ```

### Test Supabase Integration Locally

```bash
# Set Supabase credentials
export IQ_ENABLE_SUPABASE=true
export IQ_SUPABASE_URL=https://xxx.supabase.co
export IQ_SUPABASE_KEY=xxxxx

# Run server
python -m mcp_knowledge_graph

# Test operations - they'll sync to Supabase
```

### Visualize the Graph

```bash
python -m mcp_knowledge_graph.visualize \
  --input memory.jsonl \
  --output graph.html \
  --title "My Knowledge Graph"
```

Open `graph.html` in a browser to explore entities, relations, and observations.

## Contributing

### Before Submitting

1. ✅ All tests pass: `pytest`
2. ✅ Code formatted: `ruff check src/ tests/`
3. ✅ Documentation updated
4. ✅ CHANGELOG.md updated (if user-facing changes)

### Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a PR with:
   - Clear description of changes
   - Reference to related issues
   - Screenshots (if UI changes)

### Code Review Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or clearly documented)
- [ ] Follows existing code style
- [ ] Error handling appropriate
- [ ] Logging appropriate (not too verbose)

### Release Process

1. Update version in `pyproject.toml` and `version.py`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v1.3.2`
4. Push tag: `git push origin v1.3.2`
5. Deploy: `./deploy/push-and-deploy.sh`

## Additional Resources

- **Architecture**: `docs/PROJECT_OVERVIEW.md`
- **Tool Workflows**: `docs/WORKFLOWS.md`
- **Supabase Schema**: `docs/SUPABASE_SCHEMA.md`
- **Settings Flow**: `docs/SETTINGS_FLOW.md`
- **API Reference**: `README.md#api-reference-mcp-tools`

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/study-flamingo/mcp-server-memory-temporal/issues)
- **Discussions**: [GitHub Discussions](https://github.com/study-flamingo/mcp-server-memory-temporal/discussions)

