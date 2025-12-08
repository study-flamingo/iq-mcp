# File Index

- `example.env` — Environment variable descriptions and defaults

## src/mcp_knowledge_graph — Main Package

| File | Description |
|------|-------------|
| `__init__.py` | Package initialization |
| `__main__.py` | Main entry point; initializes context and starts server |
| `context.py` | Application context singleton (settings, logger, supabase) |
| `iq_logging.py` | Lazy logger proxy; defers to context after initialization |
| `manager.py` | Knowledge graph business logic and persistence |
| `models.py` | Pydantic data models (Entity, Relation, Observation, etc.) |
| `server.py` | MCP server tools and formatting helpers |
| `settings.py` | Configuration classes (AppSettings, IQSettings, SupabaseConfig) |
| `supabase_manager.py` | Supabase integration for cloud storage and email summaries |
| `supabase_utils.py` | CLI utility for Supabase operations (sync from local) |
| `version.py` | Version constants (IQ_MCP_VERSION, IQ_MCP_SCHEMA_VERSION) |
| `visualize.py` | Experimental graph visualizer |

### utils/

| File | Description |
|------|-------------|
| `migrate_graph.py` | Experimental memory migration tool |
| `schema.md` | High-level knowledge graph schema documentation |
| `seed_graph.py` | Utility to create a new default graph from scratch |

## Architecture Layers

```
version.py          ← Pure constants (no dependencies)
    ↑
settings.py         ← Config classes (no module-level side effects)
    ↑
models.py           ← Data models (imports version.py only)
    ↑
supabase_manager.py ← Imports SupabaseConfig from settings.py
    ↑
context.py          ← Runtime state container; initialized at startup
    ↑
iq_logging.py       ← Lazy logger proxy
    ↑
manager.py          ← Business logic; uses ctx for dependencies
    ↑
server.py           ← MCP tools; initializes context at startup
    ↑
__main__.py         ← Entry point
```
