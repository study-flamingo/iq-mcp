## IQ-MCP Knowledge Graph — Project Overview

- **Purpose**: Provide a temporal knowledge-graph memory for MCP tools—entities (nodes), relations (edges), and timestamped observations with durability.
- **Core qualities**: Simple JSONL persistence; strict data modeling with Pydantic v2; async-friendly server; safe, incremental evolution via metadata and schema versioning.

### High-level Architecture

- **MCP Server (`src/mcp_knowledge_graph/server.py`)**
  - Exposes user-facing tools (read, create, search, cleanup, merge, delete, update user info).
  - Formats results for LLM-friendly output.

- **Manager (`src/mcp_knowledge_graph/manager.py`)**
  - Business logic: CRUD, validation, temporal cleanup, merge, search, persistence.
  - File I/O to JSONL; handles graph assembly/validation on load.

- **Models (`src/mcp_knowledge_graph/models.py`)**
  - Pydantic v2.11 models for `Entity`, `Relation`, `Observation`, `UserIdentifier`, etc.
  - Constrained `EntityID` type; `@computed_field` for user `names`.
  - `MemoryRecord` and `GraphMeta` for storage framing and versioning.

- **Settings (`src/mcp_knowledge_graph/settings.py`)**
  - Runtime configuration and logging.

- **Utilities (`src/mcp_knowledge_graph/utils/`)**
  - Seed/migrate helpers and schema docs for the graph.

- **Optional Integrations (`src/mcp_knowledge_graph/supabase.py`)**
  - Supabase integration for external data sources (email summaries), behind feature flags.

### Data Model (essential)

- **Entity**: `id: EntityID`, `name`, `entity_type`, `observations[]`, `aliases[]`, `icon?`
- **Relation**: `from_id: EntityID`, `relation`, `to_id: EntityID` (IDs only; no special strings).
- **Observation**: `content`, `durability`, `timestamp` (auto via `default_factory`).
- **UserIdentifier**: user info + derived `names` via `@computed_field`; links to a user entity by `linked_entity_id`.

### Storage Format (JSONL)

Each line is a single JSON object:
- `{"type": "meta", "data": GraphMeta}` — optional metadata (written first when saving)
- `{"type": "user_info", "data": UserIdentifier}`
- `{"type": "entity", "data": Entity}`
- `{"type": "relation", "data": Relation}`

`GraphMeta`: `{ schema_version: int, graph_id: EntityID }`

### Validation & Conventions

- IDs are constrained strings (`EntityID`), 8-char alphanumeric.
- Relations must use entity IDs; do not embed literal names or the string `'user'`.
- Icons must be a single emoji (validated); use `Settings.no_emojis` to suppress display.
- User `names` are derived; prefer updating user fields and let the model compute.

### MCP Tools (selected)

- `read_graph`, `read_user_info`, `create_entities`, `create_relations`, `add_observations`,
  `cleanup_outdated_observations`, `get_observations_by_durability`, `delete_entry`,
  `search_nodes`, `open_nodes`, `merge_entities`, `update_user_info`.

### Evolution & Versioning

- `GraphMeta.schema_version` is written/read to support migrations.
- Add migration steps keyed by version when changing file schemas.

### At-a-glance Responsibilities

- `server.py`: tool endpoints + presentation
- `manager.py`: graph ops + persistence
- `models.py`: schema + validation + storage framing
- `settings.py`: configuration & logging
- `utils/*`: bootstrap/migration helpers
