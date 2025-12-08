# IQ-MCP Knowledge Graph MCP Server Roadmap

## Concepts

### Knowledge Graph Memory

The core concept is the knowledge graph. The graph possesses nodes and edges—Entities are nodes, Relations are edges. Knowledge about entities is grouped within the given entity and kept as a list of arbitrary string observations. Through analyzing the nodes and edges of the graph, knowledge can be kept organized and compartmentalized to mimic the way humans store memories.

### Entities

Nodes within the graph. Entities can represent anything arbitrarily, but the ideal usage is where entities represent discrete people, places, things or ideas, or describe groups of these.

- **Unique Entity IDs**: Entities are uniquely identified within the graph (8-char alphanumeric)
- **Observations**: The core memory storage modality. Observations are stored within their respective entities with durability metadata
- **Aliases**: Entities can take alternate names to make them easier to find when referenced

### Relations

Edges between nodes. Relations describe relationships between entities. Relations are atomic and give a single data point.

- **Unidirectional**: A two-way relationship is represented across two relations, one from each entity's perspective
- **ID-based**: Relation endpoints are stored with entity IDs and mapped at runtime for display

### User Information

The knowledge graph supports one primary user. The user's personal identifying information is recorded separately from observations about the user (stored in an Entity object), allowing for consistent retrieval and easy manipulation.

## Recent Improvements

- ✅ Context-based architecture (no import-time side effects)
- ✅ Lazy logger that works before and after initialization
- ✅ Daily automatic backups of memory file
- ✅ Decoupled models from settings (parameterized `icon_()` method)
- ✅ Centralized version constants

## Planned Features/Upgrades

1. **Enhance Supabase integration**
   - Consider read-side storage/cloud-first mode
   - Incremental sync instead of full replacement

2. **Fix Docker support**
   - Update Dockerfile for new architecture
   - Add docker-compose for local development

3. **Mobile device support**
   - Optimize for mobile MCP clients

4. **Implement more robust search**
   - Full-text search
   - Semantic/embedding-based search
   - Filters by entity type, date range, durability

5. **Upgrade visualizer**
   - Add editor functionality
   - Modern UI/UX
   - Real-time updates

6. **External integrations**
   - Google suite products
   - Calendar integration
   - Note-taking apps

7. **Multi-device optimization**
   - Conflict resolution
   - Sync status indicators

8. **Multi-user support**
   - Multiple profiles
   - Shared graphs
   - Access control
