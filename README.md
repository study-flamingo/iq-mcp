# Knowledge Graph MCP Server 🔮 (Python)

A knowledge graph memory system for LLMs with temporal observations. *This is a Python port of the MCP knowledge graph memory server, with some minor additions and improvements.*

An advanced implementation of persistent memory using a local knowledge graph with temporal observation support. This lets Claude remember information about users across chats with intelligent time-based categorization and automatic cleanup of outdated information.

## 🐍 Python Implementation

This is a complete Python rewrite of the original TypeScript MCP knowledge graph server, maintaining full compatibility with all features while providing improved type safety and pythonic interfaces using Pydantic models.

## ✨ Feature Improvements

In addition to the features offered by the root repository at [@shaneholloman/mcp-knowledge-graph](https://github.com/shaneholloman/mcp-knowledge-graph):

- **Temporal Observations**: Observations now include timestamps and durability categories
- **Smart Cleanup**: Automatically remove outdated temporary observations
- **Enhanced Search**: Search through both string and temporal observation formats
- **Backward Compatibility**: Existing string observations work seamlessly
- **Unified API**: Single `add_observations` tool supports both formats

## Core Concepts

### Entities

Entities are the primary nodes in the knowledge graph. Each entity has:

- A unique name (identifier)
- An entity type (e.g., "person", "organization", "event")
- A list of observations (now supporting temporal metadata)

Example:

```json
{
  "name": "John_Smith",
  "entity_type": "person",
  "observations": [
    {
      "content": "Speaks fluent Spanish",
      "timestamp": "2025-06-26T18:45:00.000Z",
      "durability": "permanent"
    }
  ]
}
```

### Relations

Relations define directed connections between entities. They are always stored in active voice and describe how entities interact or relate to each other.

Example:

```json
{
  "from": "John_Smith",
  "to": "Anthropic",
  "relation_type": "works_at"
}
```

### Temporal Observations

Observations now support temporal metadata to distinguish between permanent facts and temporary states:

#### Durability Categories

- **`permanent`**: Never expires (e.g., "Born in 1990", "Has a degree in Physics")
- **`long-term`**: Relevant for 2+ years (e.g., "Works at Acme Corp", "Lives in New York")
- **`short-term`**: Relevant for ~6 months (e.g., "Working on Project X", "Training for a marathon")
- **`temporary`**: Relevant for ~1 month (e.g., "Currently learning TypeScript", "Traveling to Dominica")

#### Observation Formats

```json
{
  "entity_name": "John_Smith",
  "observations": [
    // Simple string (defaults to long-term)
    "Likes coffee",
    
    // Temporal object with durability
    {
      "content": "Currently learning TypeScript",
      "durability": "temporary"
    },
    
    // Permanent fact
    {
      "content": "Is a software engineer",
      "durability": "permanent"
    }
  ]
}
```

## API Reference

### Core Tools

#### **create_entities**

Create multiple new entities in the knowledge graph.

**Input**: `entities` (array of objects)

- `name` (string): Entity identifier
- `entity_type` (string): Type classification  
- `observations` (string[]): Associated observations

**Behavior**: Ignores entities with existing names

#### **create_relations**

Create multiple new relations between entities.

**Input**: `relations` (array of objects)

- `from` (string): Source entity name
- `to` (string): Target entity name
- `relation_type` (string): Relationship type in active voice

**Behavior**: Skips duplicate relations

#### **add_observations** ⭐ Enhanced

Add observations with optional temporal metadata.

**Input**: `observations` (array of objects)

- `entity_name` (string): Target entity
- `contents` (array): Mix of strings and temporal objects

**Content formats**:

```python
# Simple strings (default to long-term)
["Likes coffee", "Uses Windows PC"]

# Temporal objects with durability
[
  { "content": "Is a software engineer", "durability": "permanent" },
  { "content": "Learning TypeScript", "durability": "temporary" },
  "Also likes tea"  # Mixed formats work together
]
```

**Returns**: Added observations with full temporal metadata

### Temporal Management Tools

#### **cleanup_outdated_observations** 🆕

Automatically remove observations that have exceeded their durability timeframe.

**Logic**:

- `permanent`: Never removed
- `long-term`: Removed after 24 months
- `short-term`: Removed after 6 months  
- `temporary`: Removed after 1 month

**Returns**: Summary of entities processed and observations removed

#### **get_observations_by_durability** 🆕

Retrieve observations grouped by durability category.

**Input**: `entity_name` (string)

**Returns**: Object with arrays for each durability level:

```json
{
  "permanent": [...],
  "longTerm": [...], 
  "shortTerm": [...],
  "temporary": [...]
}
```

### Standard Tools

#### **delete_entities**

Remove entities and their relations.

#### **delete_observations**  

Remove specific observations from entities.

#### **delete_relations**

Remove specific relations from the graph.

#### **read_graph**

Read the entire knowledge graph.

#### **search_nodes**

Search across entity names, types, and observation content.

#### **open_nodes**

Retrieve specific nodes by name.

## Usage Examples

### Basic Operations

```python
# Create an entity
create_entities([{
  "name": "Dr_Smith",
  "entity_type": "person", 
  "observations": ["Works at City Hospital"]
}])

# Add temporal observations
add_observations([{
  "entity_name": "Dr_Smith",
  "contents": [
    { "content": "Is a cardiologist", "durability": "permanent" },
    { "content": "Recently promoted to department head", "durability": "long-term" },
    { "content": "Currently on vacation", "durability": "temporary" },
    "Speaks three languages"  # Defaults to long-term
  ]
}])
```

### Temporal Management

```python
# View observations by durability
get_observations_by_durability("Dr_Smith")

# Clean up outdated information
cleanup_outdated_observations()
```

### Advanced Usage

```python
# Create relations
create_relations([{
  "from": "Dr_Smith",
  "to": "City_Hospital", 
  "relation_type": "works_at"
}])

# Search across all content
search_nodes("cardiologist")
```

## Installation & Setup

This MCP server is intended to be installed and run locally.

1. Clone the repository

```bash
git clone https://www.github.com/study-flamingo/mcp-knowledge-graph.git
cd mcp-knowledge-graph
```

2. Install dependencies

```bash
pip install -e .
# or using uv (recommended)
uv pip install -e .
```

3. Set up inside your MCP Client of choice, for example:

### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "mcp_knowledge_graph.server"],
      "env": {
        "MEMORY_FILE_PATH": "/path/to/your/memory.json"
      }
    }
  }
}
```

Alternatively, if installed in your environment:

```json
{
  "mcpServers": {
    "memory": {
      "command": "mcp-server-memory-temporal",
      "args": ["--memory-path", "/path/to/your/memory.json"]
    }
  }
}
```

### Environment Variables

- `MEMORY_FILE_PATH`: Custom path for memory storage (default: `memory.json`)
    *Note: The memory file path can also be specified with a command line arg, for example: `python -m mcp_knowledge_graph.server --memory-path path/to/your/memory.json`*

### Migration

If you were previously using the root project for this fork ([@shaneholloman/mcp-knowledge-graph](https://github.com/shaneholloman/mcp-knowledge-graph)), you may already have a robust memory file. Updating the old entries is not necessary, as this fork provides backwards compatibility - however if you would like to update your old memory file, the easiest way is to have your LLM manually update the `memory.jsonl` file, with using this project as context for the operation. You can do this with any MCP/LLM client capable of filesystem access (e.g., Cursor, Roo Code, Claude Code/Desktop, etc.).

## System Prompt for Temporal Memory

Knowledge graph features and utilization are greatly improved by setting a quality system prompt. As a sample, here's an enhanced system prompt that leverages temporal features:

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

**Short-term**: Current projects, temporary situations, 6-month goals
- "Learning how to play the theremin", "Finishing their high school degree"

**Temporary**: Immediate tasks, current states, monthly activities
- "Currently working on memory server", "Traveling to Saturn next week"

Use add_observations with appropriate durability categories for new information.
Regularly run cleanup_outdated_observations to maintain data quality.
```

Add this to the system prompt of your LLM. For example, on Claude Desktop:

1. Create a new project or open an existing project
2. In the project knowledge section, add the above to your Project Instructions.

## Data Format & Migration

### JSONL Storage Format

The server uses JSONL (JSON Lines) format for efficient streaming and backward compatibility:

```jsonl
{"type":"entity","name":"Dr_Smith","entity_type":"person","observations":[...]}
{"type":"relation","from":"Dr_Smith","to":"City_Hospital","relation_type":"works_at"}
```

### Backward Compatibility

- Existing string observations are automatically converted to temporal format
- Old JSONL files work without modification
- Default durability is "long-term" for legacy data

## Development

1. Clone the repository

```bash
git clone https://www.github.com/study-flamingo/mcp-knowledge-graph.git
cd mcp-knowledge-graph
```

2. Install dependencies and set up development environment

```bash
pip install -e ".[dev]"
# or using uv (recommended)
uv sync
```

3. Run tests

```bash
pytest
# or with coverage
pytest --cov=mcp_knowledge_graph
```

## Performance & Scalability

- **Automatic normalization** of legacy string observations
- **Efficient search** across mixed observation formats  
- **Smart caching** for frequently accessed data
- **Incremental cleanup** of outdated observations
- **Optimized JSON storage** for better parsing performance

## Python Features Demonstrated

This project showcases modern Python patterns:

- **Pydantic models** for type safety and validation
- **Union types** for backward compatibility  
- **Optional properties** with defaults
- **Enum classes** for durability categories
- **Type hints** throughout the codebase
- **Async/await** for non-blocking operations
- **Context managers** for resource management

## Contributing

This is a fork of the original Anthropic memory server with temporal enhancements. Key improvements:

1. **Temporal observation system** with durability categorization
2. **Enhanced API design** with unified observation handling
3. **Automatic cleanup** of outdated information
4. **Improved TypeScript architecture** with better type safety
5. **Comprehensive documentation** and examples

## Changelog

### v0.7.0 - Temporal Observations Release

- ✨ Added temporal observation support with durability categories
- ✨ Implemented automatic cleanup of outdated observations  
- ✨ Enhanced `add_observations` to support mixed formats
- ✨ Added `get_observations_by_durability` for categorized viewing
- ✨ Added `cleanup_outdated_observations` for maintenance
- 🔄 Maintained full backward compatibility with string observations
- 🏗️ Improved TypeScript interfaces and type safety
- 📚 Comprehensive documentation updates

### v0.6.3 - Base Version

- 🏗️ Original Anthropic memory server implementation
- 📝 Basic entity/relation/observation CRUD operations  
- 🔍 Simple string-based search functionality

## License

This MCP server is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License.

## Credits

Enhanced by the community with temporal observation capabilities. Original implementation by Anthropic PBC as part of the Model Context Protocol servers collection.
