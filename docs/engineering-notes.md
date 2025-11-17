## Engineering concepts to adopt (IQ-MCP)

- **Atomic file writes and locking**
  - Write to a temp file then atomically replace the target to avoid partial/corrupt files on crash:

```python
import os, tempfile

def atomic_write_text(path: str, data: str) -> None:
    dir_ = os.path.dirname(path) or '.'
    with tempfile.NamedTemporaryFile('w', delete=False, dir=dir_, encoding='utf-8') as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    os.replace(tmp_path, path)  # atomic on same FS
```

- For concurrent access, use an advisory lock (e.g., `portalocker`) around read/write.

- **Cancellation-safe async**
  - Handle `asyncio.CancelledError`, use timeouts, and ensure clean shutdown:

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

- **In-memory indexes and caches**
  - Maintain `id->entity`, `name->entity`, `alias->entity` maps to accelerate lookups; rebuild lazily on load or after mutations.
  - Consider `functools.lru_cache` for pure helpers; ensure invalidation on writes.

- **Discriminated unions for richer payloads**
  - Reduce manual routing with Pydantic discriminators:

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

- **Storage abstraction via Protocol**
  - Decouple file storage vs Supabase:

```python
from typing import Protocol

class Storage(Protocol):
    async def load(self) -> list[dict]: ...
    async def save(self, records: list[dict]) -> None: ...

async def persist(storage: Storage, records: list[dict]):
    await storage.save(records)
```

- **Static typing hygiene**
  - Use `mypy`/`pyright`; mark constants with `Final`; prefer `typing.NewType` for semantic IDs where helpful (complements constrained types).

- **Pre-commit quality gate**
  - Add `pre-commit` with: `ruff` (lint), `black` (format), `mypy` (types), `pytest` (tests).

- **Property-based testing**
  - Use `hypothesis` to fuzz (de)serialization and migration invariants (e.g., id uniqueness, relation endpoint validity).

- **Time control in tests**
  - Use `freezegun` to deterministically test observation aging/cleanup.

- **Structured logging + context**
  - Emit JSON logs or `structlog` with `graph_id`, request IDs; helps debugging across devices/backends.
  - Centralized logger module: `src/mcp_knowledge_graph/logging.py` (level via `Settings.debug`).

- **Metrics and tracing**
  - Prometheus counters/timers for tool usage; OpenTelemetry spans around IO and graph ops.

- **Advanced Pydantic features**
  - Functional validators (`AfterValidator`, `WrapValidator`) and custom serializers (`PlainSerializer`) for concise normalization/formatting.
  - `PrivateAttr` for ephemeral, non-serialized model state (e.g., in-memory indexes).

- **Computed vs persisted fields**
  - Prefer `@computed_field` for derived values; if expensive to compute, materialize on save and validate on load.

- **Schema export for tooling**
  - Use `model_json_schema()` to power the visualizer/editor and generate client types.

- **Versioned migrations (pattern)**

```python
CURRENT_SCHEMA = 1

def migrate_v1_to_v2(g): ...
def migrate_v2_to_v3(g): ...

MIGRATIONS = {1: migrate_v1_to_v2, 2: migrate_v2_to_v3}

def upgrade_if_needed(graph):
    version = (graph.meta.schema_version or 1)
    while version < CURRENT_SCHEMA:
        graph = MIGRATIONS[version](graph)
        version += 1
    graph.meta.schema_version = CURRENT_SCHEMA
    return graph
```

- **Error taxonomy**
  - Keep exception classes granular (validation vs. integrity vs. IO) and map to consistent tool-facing messages with remediation hints.

- **Safety limits**
  - Enforce maximum file size, max entities, max observations per entity, and per-request quotas.

- **CLI ergonomics**
  - Add a `typer` CLI for admin tasks: validate, migrate, compact, inspect.

- **Config layering**
  - Use `pydantic-settings` for env/file/CLI overrides to ease deployment (Supabase, Docker).
