## Engineering Concepts (IQ-MCP)

### Context-Based Architecture

The application uses a singleton `AppContext` to manage runtime state:

```python
from .context import ctx

# Initialize once at startup
ctx.init()

# Access anywhere after initialization
ctx.settings.debug
ctx.logger.info("...")
if ctx.supabase:
    await ctx.supabase.get_email_summaries()
```

**Benefits:**
- No import-time side effects
- Explicit initialization point
- Easy dependency injection for testing
- Clean separation of config vs runtime state

### Atomic File Writes and Backups

Write to a temp file then atomically replace to avoid partial/corrupt files:

```python
import os, tempfile

def atomic_write_text(path: str, data: str) -> None:
    dir_ = os.path.dirname(path) or '.'
    with tempfile.NamedTemporaryFile('w', delete=False, dir=dir_, encoding='utf-8') as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    os.replace(tmp_path, path)  # atomic on same FS
```

**Daily Backups**: The manager automatically creates daily backups after each save:
- Stored in `backups/` subdirectory alongside memory file
- Named with date suffix: `memory_2025-11-25.jsonl`
- Only one backup per day (skips if already exists)

### Cancellation-Safe Async

Handle `asyncio.CancelledError`, use timeouts, and ensure clean shutdown:

```python
import asyncio

async def run_server(app):
    try:
        async with asyncio.timeout(30):
            await app.start()
    except asyncio.CancelledError:
        await app.stop()
        raise
```

### In-Memory Indexes and Caches

Maintain `id->entity`, `name->entity`, `alias->entity` maps to accelerate lookups:

```python
async def get_entity_id_map(self, graph: KnowledgeGraph) -> dict[EntityID, Entity]:
    return {e.id: e for e in graph.entities}
```

Consider `functools.lru_cache` for pure helpers; ensure invalidation on writes.

### Discriminated Unions for Richer Payloads

Reduce manual routing with Pydantic discriminators:

```python
from typing import Annotated, Union
from pydantic import BaseModel, Field

class AddEntity(BaseModel):
    kind: str = Field('add_entity', frozen=True)
    name: str

class AddRelation(BaseModel):
    kind: str = Field('add_relation', frozen=True)
    relation: str

Command = Annotated[Union[AddEntity, AddRelation], Field(discriminator='kind')]
```

### Storage Abstraction via Protocol

Decouple file storage vs Supabase:

```python
from typing import Protocol

class Storage(Protocol):
    async def load(self) -> list[dict]: ...
    async def save(self, records: list[dict]) -> None: ...

async def persist(storage: Storage, records: list[dict]):
    await storage.save(records)
```

### Static Typing Hygiene

- Use `mypy`/`pyright`
- Mark constants with `Final`
- Prefer `typing.NewType` for semantic IDs
- Use `TYPE_CHECKING` for import-only types

### Pre-Commit Quality Gate

Add `pre-commit` with: `ruff` (lint), `black` (format), `mypy` (types), `pytest` (tests).

### Property-Based Testing

Use `hypothesis` to fuzz (de)serialization and migration invariants:
- ID uniqueness
- Relation endpoint validity
- Round-trip serialization

### Time Control in Tests

Use `freezegun` to deterministically test observation aging/cleanup.

### Structured Logging + Context

The lazy logger in `iq_logging.py` proxies to `ctx.logger` after initialization:

```python
from .iq_logging import logger

# Works before ctx.init() (uses bootstrap logger)
# Works after ctx.init() (uses configured logger)
logger.info("message")
```

Emit JSON logs or use `structlog` with `graph_id`, request IDs for debugging.

### Metrics and Tracing

Consider Prometheus counters/timers for tool usage; OpenTelemetry spans around IO.

### Advanced Pydantic Features

- Functional validators (`AfterValidator`, `WrapValidator`)
- Custom serializers (`PlainSerializer`)
- `PrivateAttr` for ephemeral, non-serialized state
- `@computed_field` for derived values (e.g., user `names`)

### Schema Export for Tooling

Use `model_json_schema()` to power visualizer/editor and generate client types.

### Versioned Migrations

```python
from .version import IQ_MCP_SCHEMA_VERSION

MIGRATIONS = {1: migrate_v1_to_v2, 2: migrate_v2_to_v3}

def upgrade_if_needed(graph):
    version = (graph.meta.schema_version or 1)
    while version < IQ_MCP_SCHEMA_VERSION:
        graph = MIGRATIONS[version](graph)
        version += 1
    graph.meta.schema_version = IQ_MCP_SCHEMA_VERSION
    return graph
```

### Error Taxonomy

Keep exception classes granular:
- `KnowledgeGraphException`: Graph interaction errors
- `ValueError`: Data validation errors
- `RuntimeError`: Integrity/IO errors

Map to consistent tool-facing messages with remediation hints.

### Safety Limits

Enforce maximum file size, max entities, max observations per entity, and per-request quotas.

### CLI Ergonomics

Add a `typer` CLI for admin tasks: validate, migrate, compact, inspect.

### Config Layering

Settings use layered precedence:
1. CLI arguments
2. Environment variables
3. Defaults

See `docs/SETTINGS_FLOW.md` for details.
