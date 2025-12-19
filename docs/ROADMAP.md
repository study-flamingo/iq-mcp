# IQ-MCP Knowledge Graph Server — Roadmap

**Vision**: A universal, drop-in MCP server that provides persistent knowledge graph memory across all MCP-capable clients and platforms, without sacrificing functionality or requiring client-specific adaptations.

**Target Users**: Individual users who want a memory system that is system-agnostic, can track tasks/projects, and can provide different sets of context depending on what is relevant to the user's requests.

## Core Principles

1. **Client Agnosticism**: Works identically across Claude Desktop, Cursor, Roo Code, and any MCP-compliant client
2. **Platform Independence**: Functions seamlessly on Windows, macOS, Linux, and mobile devices
3. **Modular Architecture**: Robust core with optional features that can be enabled/disabled based on user preferences
4. **Backward Compatibility**: All upgrades maintain compatibility with existing data and workflows
5. **Performance First**: Optimized for fast responses, even with large knowledge graphs
6. **Data Portability**: Progressive enhancement - core works everywhere, advanced features when possible

## Core Value Propositions

1. **Temporal Observations with Durability**: Smart memory management with automatic cleanup
2. **Project/Task Context Awareness**: Automatic current project detection and highlighting
3. **Knowledge Graph Structure**: Entities + relations for organized memory
4. **Memory Visualization & Management**: Tools to understand and manually manage the graph
5. **Data Source Integration**: Optional integrations with email, calendar, Slack, Zapier, etc.

---

## Short-Term Roadmap (v1.5.0 - v1.7.0)

### v1.5.0 - Project & Task Management (Next Release)

**Goal**: Enable users to track projects and tasks within the knowledge graph, with automatic context detection.

**Features**:
- **Project Management System**
  - Separate `Project` and `Task` data models (not entities)
  - Project status tracking (planning, active, on-hold, completed, cancelled)
  - Priority levels and date tracking
  - Optional linking to entities in knowledge graph
  - Tags for categorization

- **Task Management System**
  - Tasks linked to projects (required relationship)
  - Task status (todo, in-progress, blocked, completed, cancelled)
  - Dependencies between tasks
  - Assignee linking (to person entities)
  - Due dates and completion tracking

- **Current Project Detection**
  - Multi-method detection: explicit mentions, entity relations, recent observations
  - Automatic highlighting of project context in `read_graph`
  - `get_current_project()` tool for LLM context awareness
  - `highlight_current_project()` tool for automatic context presentation

- **MCP Tools**
  - `create_projects`, `update_project`, `view_projects`, `view_project`
  - `create_tasks`, `update_task`, `view_tasks`, `view_task`
  - `get_current_project`, `highlight_current_project`

- **Storage**
  - JSONL format: `{"type": "project", "data": Project}` and `{"type": "task", "data": Task}`
  - Supabase tables: `kgProjects`, `kgTasks` (with foreign keys)

**Impact**: Enables LLMs to understand and highlight current work context automatically.

---

### v1.6.0 - Enhanced & Semantic Search

**Goal**: Make the knowledge graph more discoverable with both keyword and semantic search capabilities.

**Features**:
- **Advanced Keyword Search**
  - Full-text search across all fields (names, aliases, observations, relations)
  - Filter by entity type, durability, date ranges
  - Search by tags (when added to entities)
  - Fuzzy matching for typos and variations

- **Query Language**
  - Simple query DSL for complex searches
  - Examples: "entities where type=person and has observation containing 'engineer'"
  - Date-based queries: "observations added in last 30 days"
  - Relation queries: "entities related to X via relation Y"

- **Semantic Search (Optional)**
  - Embedding generation for entities and observations (server-side)
  - Vector storage (Supabase pgvector or local)
  - "Find entities similar to X" queries
  - Natural language queries: "people I work with"
  - Configurable embedding models (OpenAI, local models, etc.)

- **Hybrid Search**
  - Combine keyword and semantic search
  - Configurable search strategy
  - Result ranking with both methods

- **Performance**
  - Search result caching
  - Indexed lookups for common queries
  - Pagination support for large result sets

**Impact**: Users can find information quickly using both keyword matching and meaning-based search.

---

### v1.7.0 - Export/Import & Enhanced Backup Options

**Goal**: Enable data portability and robust backup/restore across platforms and clients.

**Features**:
- **Export Formats**
  - JSON export (full graph dump)
  - CSV export (entities, relations, observations as tables)
  - Markdown export (human-readable format)
  - GraphML export (for visualization tools)

- **Import Capabilities**
  - Import from JSON (full restore)
  - Import from CSV (bulk entity creation)
  - Merge imports (conflict resolution)
  - Validation and error reporting

- **Backup Options Beyond JSONL**
  - Cloud backup to Supabase (if enabled)
  - S3/object storage backup (optional)
  - Git-based backup (versioned history)
  - Encrypted backup option
  - Automatic backup rotation (keep last N backups)
  - Backup verification tools

- **Backup/Restore Tools**
  - `export_graph(format)` MCP tool
  - `import_graph(data, merge_strategy)` MCP tool
  - `backup_graph(destination, encryption)` MCP tool
  - `restore_graph(backup_source)` MCP tool

- **Data Migration**
  - Version-aware migration helpers
  - Schema upgrade tools
  - Data validation after import

**Impact**: Users can move between clients/platforms without data loss, and maintain multiple backup strategies.

---

## Medium-Term Roadmap (v2.0.0 - v2.2.0)

### v2.0.0 - Multi-Device Sync & Conflict Resolution

**Goal**: Seamless synchronization across multiple devices and clients for individual users.

**Features**:
- **Conflict Resolution**
  - Last-write-wins with timestamps
  - Merge strategies for non-conflicting changes
  - Conflict detection and reporting
  - Manual conflict resolution tools

- **Sync Status**
  - Sync indicators in responses
  - Last sync timestamp tracking
  - Sync conflict notifications
  - Offline mode support

- **Incremental Sync**
  - Only sync changes since last sync
  - Delta compression
  - Efficient network usage

- **Multi-Client Coordination**
  - Works with multiple clients simultaneously
  - No data loss when switching clients
  - Consistent state across devices

**Impact**: True multi-device, multi-client support without data conflicts for individual users.

---

### v2.1.0 - Data Source Integrations (Optional Features)

**Goal**: Enable optional integrations with external data sources to enrich the knowledge graph.

**Features**:
- **Email Integration** (already partially implemented via Supabase)
  - Enhanced email summary processing
  - Entity extraction from emails
  - Automatic relation creation from email threads

- **Calendar Integration** (Optional)
  - Import calendar events as entities
  - Link events to projects/tasks
  - Extract participants and locations

- **Slack Integration** (Optional)
  - Import Slack messages as observations
  - Extract mentions as entities
  - Link channels to projects

- **Zapier/Webhook Integration** (Optional)
  - Generic webhook receiver
  - Custom integration templates
  - Event-driven graph updates

- **Modular Integration System**
  - Each integration is optional and can be enabled/disabled
  - Integration configuration via settings
  - No core functionality depends on integrations

**Impact**: Knowledge graph automatically enriches from user's existing data sources.

---

### v2.2.0 - Mobile Optimization & Lightweight Mode

**Goal**: Optimize for mobile MCP clients and resource-constrained environments.

**Features**:
- **Lightweight Mode**
  - Reduced memory footprint
  - Streaming responses for large datasets
  - Lazy loading of observations
  - Configurable data limits

- **Mobile-Specific Optimizations**
  - Smaller payload sizes
  - Efficient JSON serialization
  - Network-aware sync (WiFi vs cellular)
  - Battery-conscious operations

- **Progressive Enhancement**
  - Core features work everywhere
  - Advanced features available when resources allow
  - Graceful degradation

**Impact**: Full functionality on mobile devices without performance degradation.

---

## Long-Term Vision (v2.3.0+)

### v2.3.0 - Advanced Visualization & Graph Analysis

**Goal**: Provide graph visualization and analysis tools that work across clients.

**Features**:
- **Graph Analysis Tools**
  - Entity relationship graphs
  - Clustering and community detection
  - Centrality metrics (most connected entities)
  - Temporal analysis (how graph changes over time)

- **Visualization Export**
  - Interactive HTML graphs (D3.js, Cytoscape.js)
  - Static image exports (PNG, SVG)
  - GraphML for external tools (Gephi, yEd)

- **MCP Tools for Analysis**
  - `analyze_graph()` - Get graph statistics
  - `visualize_entity_network(entity_id)` - Subgraph visualization
  - `find_related_entities(entity_id, depth)` - Relationship discovery

- **Client-Agnostic Visualization**
  - Server generates visualization data
  - Clients render using their preferred method
  - Fallback to text-based representation

**Impact**: Users can understand their knowledge graph structure regardless of client capabilities.

---

### v3.0.0 - Multi-User Support (Revisit)

**Goal**: Support shared knowledge graphs and collaborative editing (if needed).

**Note**: This is deferred to v3.0.0 and will be reconsidered based on user feedback and needs.

**Potential Features** (if needed):
- User authentication and authorization
- Per-user graphs with optional sharing
- Shared project spaces
- Access control (read/write permissions)
- Change attribution

---

## Out of Scope (For Now)

These features are explicitly **not** planned, as they don't align with the core vision:

- **Plugin Architecture/Ecosystem**: Instead, optional features ship with the product as modular components
- **AI-Powered Insights**: Insights come from the MCP client LLM, not this server
- **Real-Time Collaboration**: Doesn't make sense for individual-focused use case
- **Rich Client-Side Visualization**: Visualization is server-generated data that clients can render as they prefer

---

## Technical Debt & Maintenance

### Code Quality
- [ ] Comprehensive test coverage (aim for 90%+)
- [ ] Type hints throughout codebase
- [ ] API documentation generation
- [ ] Performance benchmarking suite

### Infrastructure
- [ ] CI/CD pipeline for automated testing and deployment
- [ ] Monitoring and alerting
- [ ] Automated backup verification
- [ ] Health check endpoints

### Documentation
- [ ] Client integration guides (per client)
- [ ] API reference documentation
- [ ] Architecture decision records (ADRs)
- [ ] Migration guides for all versions

---

## Success Metrics

### Client Agnosticism
- ✅ Works identically in Claude Desktop, Cursor, Roo Code
- ✅ No client-specific code paths
- ✅ Feature parity across all clients

### Performance
- ✅ Sub-100ms response times for common operations
- ✅ Handles graphs with 10,000+ entities efficiently
- ✅ Low memory footprint (<100MB for typical graphs)

### Reliability
- ✅ 99.9% uptime for cloud deployments
- ✅ Zero data loss in normal operations
- ✅ Automatic recovery from errors

### Developer Experience
- ✅ Easy local setup (<5 minutes)
- ✅ Clear error messages
- ✅ Comprehensive logging

---

## Notes

- **Versioning**: Follows Semantic Versioning (MAJOR.MINOR.PATCH)
- **Schema Version**: Separate `IQ_MCP_SCHEMA_VERSION` for storage format changes
- **Backward Compatibility**: Maintained for at least 2 major versions
- **Breaking Changes**: Only in major versions, with migration guides
- **Modularity**: Optional features (integrations, semantic search) can be enabled/disabled without affecting core

---

## Contributing Ideas

Have a feature idea that enhances cross-platform compatibility, client agnosticism, or individual knowledge management? We'd love to hear it! Please open an issue or discussion on GitHub.
