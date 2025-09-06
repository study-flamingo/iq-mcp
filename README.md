# IQ-MCP Knowledge Graph Server 🔮 (Python)

A FastMCP 2.11 server that provides a temporal knowledge graph memory for LLMs. It enables persistent, searchable memory with timestamped observations, durability categories, alias-aware entity resolution, and ergonomic tools for creating, searching, maintaining, merging, and visualizing your memory graph.

This is a modern Python implementation using Pydantic models and FastMCP, designed for drop-in use with MCP clients (Claude Desktop, Cursor, Roo Code, etc.).

## ✨ Highlights

  - **Temporal observations** with durability categories and automatic timestamps
  - **Smart cleanup** that removes outdated observations by durability
  - **Alias-aware graph**: resolve entities by name or any alias
  - **Unified tools**: single `create_entry` and `delete_entry` cover CRUD
  - **Merge entities**: consolidate duplicates while preserving relations and aliases
  - **Enhanced search** across names, aliases, types, and observation content
  - **Flexible storage**: robust JSONL reader supports nested and legacy-ish formats

## Core Concepts

### Entities

Entities are the primary nodes in the knowledge graph. Each entity has:

  - A unique name (identifier)
  - An entity type (e.g., "person", "organization", "event")
  - A list of timestamped observations (with durability)
  - Optional aliases (alternative names that map to the same entity)

Example:

```json
{
  "name": "John_Smith",
  "entity_type": "person",
  "aliases": ["Johnny Smith", "John S."],
  "observations": [
    {
      "content": "Speaks fluent Spanish",
      "ts": "2025-06-26T18:45:00.000Z",
      "durability": "permanent"
    }
  ]
}
```

### Relations

Relations define directed connections between entities. They are stored in active voice and describe how entities interact or relate to each other.

```json
{
  "from": "John_Smith",
  "to": "Anthropic",
  "relation_type": "works_at"
}
```

### Temporal Observations

Observations include durability and an ISO timestamp to distinguish durable facts from transient state.

Durability categories:
  - `permanent`: Never expires (e.g., "Born in 1990")
  - `long-term`: Relevant for ~1+ years (e.g., "Works at Acme Corp")
  - `short-term`: Relevant for ~3 months (e.g., "Working on Project X")
  - `temporary`: Relevant for ~1 month (e.g., "Currently learning TypeScript")

## API Reference (FastMCP Tools)

### Core, Unified CRUD

#### create_entry

Add observations, entities, or relations.

  - Request: `CreateEntryRequest`
  - Fields:
    - `entry_type`: one of `"observation" | "entity" | "relation"`
    - `data`: list of the appropriate objects for the chosen type

Examples:

```json
{ "entry_type": "entity", "data": [
  { "name": "Dr_Smith", "entity_type": "person", "aliases": ["Doctor Smith"] }
]}
```

```json
{ "entry_type": "relation", "data": [
  { "from": "Dr_Smith", "to": "City_Hospital", "relation_type": "works_at" }
]}
```

```json
{ "entry_type": "observation", "data": [
  { "entityName": "Dr_Smith", "observation": [
    { "content": "Currently on vacation", "durability": "temporary", "ts": null },
    { "content": "Speaks three languages", "durability": "long-term", "ts": null }
  ] }
]}
```

Notes:
  - Entity lookups are alias-aware; you can use the entity's name or any alias.
  - Timestamps are added automatically; you may pass `"ts": null` for convenience.

#### delete_entry

Delete observations, entities, or relations.

  - Request: `DeleteEntryRequest`
  - Fields:
    - `entry_type`: `"observation" | "entity" | "relation"`
    - `data`:
      - entities: `list[str]` of names or aliases
      - observations: `list[DeleteObservationRequest]` with `{ entityName, observation: ["content to delete", ...] }`
      - relations: `list[Relation]` with `{ from, to, relation_type }`

This action is destructive and irreversible. Always confirm with the user before invoking.

### Graph Operations

  - `read_graph()`: Returns full graph. Observations are sorted by newest first.
  - `search_nodes(query)`: Matches names, aliases, types, and observation content.
  - `open_nodes(entity_names)`: Returns only the requested nodes and their inter-relations (name or alias supported).
  - `merge_entities(newentity_name, entity_names)`: Merge multiple entities into a single entity. Combines observations (deduped), rewrites relations, and aggregates aliases. Prevents name/alias conflicts.

### Temporal Management

  - `cleanup_outdated_observations()`
    - permanent: never removed
    - long-term: removed after > ~12 months
    - short-term: removed after > ~3 months
    - temporary: removed after > ~1 month
    - Returns counts plus details of removed observations

  - `get_observations_by_durability(entity_name)`: Returns groups `permanent`, `long_term`, `short_term`, `temporary`.

## Usage Examples

### Create entities, relations, and observations

```json
{ "entry_type": "entity", "data": [
  { "name": "Dr_Smith", "entity_type": "person", "aliases": ["Doctor Smith"] }
]}
```

```json
{ "entry_type": "relation", "data": [
  { "from": "Dr_Smith", "to": "City_Hospital", "relation_type": "works_at" }
]}
```

```json
{ "entry_type": "observation", "data": [
  { "entityName": "Dr_Smith", "observation": [
    { "content": "Is a cardiologist", "durability": "permanent", "ts": null },
    { "content": "Recently promoted to department head", "durability": "long-term", "ts": null },
    { "content": "Currently on vacation", "durability": "temporary", "ts": null }
  ] }
]}
```

### Temporal management

```json
{ "tool": "get_observations_by_durability", "params": { "entity_name": "Dr_Smith" } }
```

```json
{ "tool": "cleanup_outdated_observations", "params": {} }
```

### Search and open

```json
{ "tool": "search_nodes", "params": { "query": "cardiologist" } }
```

```json
{ "tool": "open_nodes", "params": { "entity_names": ["Dr_Smith", "City_Hospital"] } }
```

### Merge

```json
{ "tool": "merge_entities", "params": { "newentity_name": "John_Smith", "entity_names": ["John", "Johnny", "J. Smith"] } }
```

## Installation & Setup

This server is intended to run locally under FastMCP-compatible clients.

1) Clone and install

```bash
git clone https://www.github.com/study-flamingo/mcp-knowledge-graph.git
cd mcp-knowledge-graph
pip install -e .
# or using uv (recommended)
uv pip install -e .
```

2) Configure your MCP client (Claude Desktop example)

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "mcp_knowledge_graph.server", "--memory-path", "/absolute/path/to/memory.jsonl"],
      "env": {
        "IQ_TRANSPORT": "stdio",
        "IQ_DEBUG": "false"
      }
    }
  }
}
```

Notes:
  - Default transport is `stdio`. You can also use `http` or `sse` by setting `IQ_TRANSPORT` (aliases like `streamable-http` are normalized to `http`).
  - Memory path may be provided via CLI `--memory-path` or environment `IQ_MEMORY_PATH`.

3) Optional: HTTP transport (for streamable clients)

```bash
IQ_TRANSPORT=http IQ_STREAMABLE_HTTP_PORT=8000 \
python -m mcp_knowledge_graph.server --memory-path /absolute/path/to/memory.jsonl
```

### Configuration (env and CLI)

Env vars (with CLI equivalents):
  - `IQ_MEMORY_PATH` (or `--memory-path`): path to `memory.jsonl` (default: repo root `memory.jsonl`, fallback: `example.jsonl` if present)
  - `IQ_TRANSPORT` (or `--transport`): `stdio` | `http` | `sse`
  - `IQ_STREAMABLE_HTTP_PORT` (or `--port`): port for `http` transport (default: 8000)
  - `IQ_STREAMABLE_HTTP_HOST` (or `--http-host`)
  - `IQ_STREAMABLE_HTTP_PATH` (or `--http-path`)
  - `IQ_DEBUG` (or `--debug`): `true` enables verbose logging

### Migration

If you were using the original project, your JSONL files should work as long as entity and relation records are well-formed. Loader accepts nested `data` format and a flattened format; invalid lines are skipped with a warning. Saving uses the modern nested format.

## System Prompt for Temporal Memory

Knowledge graph usage improves with a good system prompt. Example:

```markdown
# Memory Tool Usage

Follow these steps for conversational interactions:

## User Identification:
You should assume that you are interacting with the `default_user`.
If you have not identified default_user, proactively try to do so.

## Memory Retrieval:
Always begin a new conversation by retrieving all relevant information from your knowledge graph
Always refer to your knowledge graph as your "memory"

## Memory Gathering:
While conversing with the user, be attentive to any new information that falls into these categories:
a) Professional Identity (job title, specializations, software development skills, certifications, business roles, etc.)
b) Domain-Specific Knowledge (work protocols, project details, scheduling patterns, equipment, software systems, workflow optimizations, etc.)
c) Technical Projects (current development projects, programming languages, frameworks, AI tools, automation workflows, deployment environments, etc.)
d) Learning & Development (new technologies being explored, courses taken, conferences attended, skill gaps, learning goals, etc.)
e) Professional Network (colleagues, software development contacts, AI/tech community connections, business partners, mentors, etc.)
f) Task Management (recurring responsibilities, project deadlines, appointment patterns, development milestones, automation opportunities, etc.)
g) Tools & Systems (domain-specific software, development tools, AI assistants, productivity apps, integrations, pain points, etc.)
h) Business Operations (KPIs, revenue goals, efficiency improvements, technology investments, growth strategies, etc.)

## Memory Update with Temporal Awareness:
If any new information was gathered during the interaction, update your memory using appropriate durability:

**Permanent**: Core identity, fundamental skills, permanent relationships
- "Is a software engineer", "Has a degree in Computer Science", "Full name is Ada Lovelace"

**Long-term**: Stable preferences, established systems, long-term goals
- "Uses VS Code", "Enjoys long walks on the beach", "Prefers Python"

**Short-term**: Current projects, temporary situations, 3-month goals
- "Learning how to play the theremin", "Finishing their high school degree"

**Temporary**: Immediate tasks, current states, monthly activities
- "Currently working on memory server", "Traveling to Saturn next week"

Use `create_entry` with `entry_type="observation"` and appropriate durability when adding new information.
Regularly run `cleanup_outdated_observations` to maintain data quality.
```

## Data Format & Migration

### JSONL Storage Format

IQ_MCP stores data in a JSONL file. Entities and Relations are discrete objects and tie Entities together.

Information about the user is stored in the `default_user` object. Within the file is an identifier that provides the user's
real name, and several possible variations (nickname, etc.).

Save file format:

  - `__default_user__` identifier

```jsonl
{"type":"entity","data":{"name":"Dr_Smith","entity_type":"person","observation":[{"contents":"Is a cardiologist","durability":"permanent","ts":"2025-01-01T00:00:00"}],"alias":["Doctor Smith"]}}
{"type":"relation","data":{"from":"Dr_Smith","to":"City_Hospital","relation_type":"works_at"}}
```

### Backward Compatibility

  - Loader tolerates both nested (`{"type":"entity","data":{...}}`) and flattened (`{"type":"entity", ...}`) variants
  - Lines that are malformed are skipped with warnings rather than failing the entire load

## Development

1) Install dev deps and sync

```bash
pip install -e ".[dev]"
uv sync
```

2) Run tests

```bash
pytest
pytest --cov=mcp_knowledge_graph
```

3) Visualize a graph (optional)

```bash
python -m mcp_knowledge_graph.visualize --input memory.jsonl --output graph.html --title "Knowledge Graph"
```

Open `graph.html` to explore nodes, aliases, observations, and relations with an interactive D3 view.

## Performance & Scalability

  - **Efficient search** across names, aliases, types, and observation content  
  - **Incremental cleanup** of outdated observations
  - **Optimized JSONL storage**

## Python Features Demonstrated

  - **FastMCP 2.11** server tools
  - **Pydantic** models with field aliases
  - **Enums** for durability
  - **Type hints** throughout
  - **Async/await** where appropriate

## Contributing

Key improvements over the original baseline:

1) Temporal observation system with durability categorization and timestamps
2) Unified CRUD via `create_entry`/`delete_entry`
3) Alias-aware entity resolution and search
4) Entity merge with relation rewrite and alias aggregation
5) Robust JSONL reader and safer persistence

## Changelog

### Recent

  - ✨ Temporal observations with durability + timestamps
  - ✨ Unified tools: `create_entry`, `delete_entry`
  - ✨ `merge_entities` tool for dedupe/consolidation
  - ✨ Alias-aware operations across tools
  - 🔄 Backward-friendly JSONL loading (nested and flattened)

## License

This MCP server is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License.

## Credits

Enhanced by the community with temporal observation capabilities. Original implementation by Anthropic PBC as part of the Model Context Protocol servers collection.
