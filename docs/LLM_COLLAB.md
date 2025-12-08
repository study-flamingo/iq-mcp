<!-- markdownlint-disable -->
## Collaborating with an LLM — Guidelines

### Mission & Guardrails

- Prioritize correctness, data integrity, and backward compatibility.
- Keep edits minimal and scoped; do not refactor unrelated code.
- Prefer model-level validation (Pydantic) over ad-hoc checks sprinkled across code.
- Preserve storage invariants and schema versioning.

### Key Files to Understand

| File | Purpose |
|------|---------|
| `context.py` | Runtime state singleton (settings, logger, supabase) |
| `settings.py` | Configuration classes (no module-level side effects) |
| `models.py` | Data models (no runtime dependencies) |
| `manager.py` | Business logic and persistence |
| `server.py` | MCP tools and formatting |
| `version.py` | Version constants |

### Workflow Checklist (for any change)

1. Read the relevant files first; understand the context-based architecture.
2. Identify validation paths; prefer constrained types, `validation_alias`, and `default_factory`.
3. Ensure JSONL storage remains valid (`MemoryRecord` types: meta, user_info, entity, relation).
4. If introducing breaking changes in storage, add a migration keyed by `IQ_MCP_SCHEMA_VERSION`.
5. Update or add tests/docs if the public tool surface changes.
6. Access settings via `ctx.settings`, not direct imports.

### Coding Style & Conventions

- Naming: descriptive function and variable names; avoid cryptic abbreviations
- Control flow: early returns; shallow nesting; meaningful error handling
- Pydantic v2 patterns:
  - Constrained types via `Annotated[..., Field(...)]` (e.g., `EntityID`)
  - `default_factory` for timestamps/IDs; avoid post-hoc validators for defaults
  - `@computed_field` for derived data (e.g., user `names`)
- Relations: IDs only (no literal names or special `'user'` token)
- Icons: must be a single emoji; pass `use_emojis` parameter to `icon_()` method

### Context Pattern

The application uses a singleton context initialized at startup:

```python
from .context import ctx

# At startup (in __main__.py or server.py):
ctx.init()

# Anywhere else:
ctx.settings.debug
ctx.logger.info("...")
ctx.supabase  # SupabaseManager or None
```

**Do not** import settings directly from `settings.py` at module level. Use `ctx.settings` after initialization.

### Storage & Migrations

- JSONL records are parsed via `MemoryRecord.model_validate_json()`
- The first line may be `meta`; attach it to `KnowledgeGraph.meta`
- Migration hook pattern:

```python
from .version import IQ_MCP_SCHEMA_VERSION

MIGRATIONS = {1: migrate_v1_to_v2}

def upgrade_if_needed(graph):
    version = (graph.meta.schema_version or 1)
    while version < IQ_MCP_SCHEMA_VERSION:
        graph = MIGRATIONS[version](graph)
        version += 1
    graph.meta.schema_version = IQ_MCP_SCHEMA_VERSION
    return graph
```

### Typical Safe Changes (Examples)

- New MCP tool that composes existing manager methods
- Additional validators using Pydantic features rather than manual checks
- Improving result formatting or adding optional fields (non-breaking output)
- Adding new optional config to `SupabaseConfig` or `IQSettings`

### Risky Changes (Avoid or Gate Behind Migrations)

- Changing JSONL layout or record types without version-aware loaders
- Altering semantics of IDs, relation endpoints, or user linking
- Expensive recomputation in `@computed_field` without consideration for load performance
- Adding module-level side effects that run on import

### Testing & Observability

- Add tests for persistence and validation; use fixed time to test observation aging
- Prefer structured logs with context (graph_id, operation)
- The lazy logger works before and after `ctx.init()`

### Communication in PRs/Edits

- Include: intent, scope, data model impact, migration needs, and testing notes
- Keep edits focused and reversible
- Reference the relevant sections of this doc
