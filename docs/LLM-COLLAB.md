## Collaborating with an LLM — Guidelines

### Mission & Guardrails

- Prioritize correctness, data integrity, and backward compatibility.
- Keep edits minimal and scoped; do not refactor unrelated code.
- Prefer model-level validation (Pydantic) over ad-hoc checks sprinkled across code.
- Preserve storage invariants and schema versioning.

### Workflow Checklist (for any change)

1. Read the relevant files first (`server.py`, `manager.py`, `models.py`, `settings.py`).
2. Identify validation paths; prefer constrained types, `validation_alias`, and `default_factory`.
3. Ensure JSONL storage remains valid (`MemoryRecord` types: meta, user_info, entity, relation).
4. If introducing breaking changes in storage, add a migration keyed by `GraphMeta.schema_version`.
5. Update or add tests/docs if the public tool surface changes.

### Coding Style & Conventions

- Naming: descriptive function and variable names; avoid cryptic abbreviations (OK in v. small functions, loops, etc.)
- Control flow: early returns; shallow nesting; meaningful error handling.
- Pydantic v2.11 patterns:
  - Constrained types via `Annotated[..., Field(...)]` (e.g., `EntityID`).
  - `validation_alias=AliasChoices(...)` for legacy/compat inputs.
  - `default_factory` for timestamps/IDs; avoid post-hoc validators for defaults.
  - `@computed_field` for derived data (e.g., user `names`).
- Relations: IDs only (no literal names or special `'user'` token).
- Icons: must be a single emoji; gracefully ignore if disabled via settings.

### Storage & Migrations

- JSONL records are parsed via `MemoryRecord.model_validate_json()`.
- The first line may be `meta`; attach it to `KnowledgeGraph.meta`.
- Migration hook pattern:

```python
CURRENT_SCHEMA = 1
MIGRATIONS = { 1: migrate_v1_to_v2 }

def upgrade_if_needed(graph):
    version = (graph.meta.schema_version or 1)
    while version < CURRENT_SCHEMA:
        graph = MIGRATIONS[version](graph)
        version += 1
    graph.meta.schema_version = CURRENT_SCHEMA
    return graph
```

### Typical Safe Changes (Examples)

- New MCP tool that composes existing manager methods.
- Additional validators using Pydantic features rather than manual checks.
- Improving result formatting or adding optional fields (non-breaking output).

### Risky Changes (Avoid or Gate Behind Migrations)

- Changing JSONL layout or record types without version-aware loaders.
- Altering semantics of IDs, relation endpoints, or user linking.
- Expensive recomputation in `@computed_field` without consideration for load performance.

### Testing & Observability

- Add tests for persistence and validation; use fixed time to test observation aging.
- Prefer structured logs with context (graph_id, operation).

### Communication in PRs/Edits

- Include: intent, scope, data model impact, migration needs, and testing notes.
- Keep edits focused and reversible; reference the relevant sections of this doc.
