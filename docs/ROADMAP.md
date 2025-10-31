# IQ-MCP Knowledge Graph MCP Server Roadmap

## Concepts

### Knowledge graph memory

The core concept is the knowledge graph. The graph posesses nodes and edges - Entities are nodes, Relations are edges. Knowledge about entities is grouped within the given entity and kept as a list of arbitrary string observations. Through analyzing the nodes and edges of the graph, knowledge can be kept organized and compartmentalized to mimic the way humans store memories.

### Entities

Nodes within the graph. Entities can represent anything arbitrarily, but the ideal usage is where entities represent discrete people, places, things or ideas, or describe groups of these.

  - Unique Entity IDs: Entities are uniquely identified within the graph.
  - Observations: The core memory storage modality. Observations are stored within their respective entities.
  - Aliases: Entities can take alternate names in order to make them easier to find when they are referenced by the user, and all the other reasons aliases make sense when handling natural language requests.

### Relations

Edges of nodes. As implied, relations describe relationships between entities. Observations can be arbitrary, but the ideal usage is where relations are atomic and give a single data point.

  - Unidirectional: A two-way relationship between entities would be represented across two observations, one describing the relation from each entity's perspective. This allows for asymmetric relations between entities.
  - Relation entities (to/from) are stored with their corresponding entity IDs and mapped at runtime for human-friendly display.

### Independently-managed user information

At present, the knowledge graph system supports only one primary user. The user's personal identifying information is recorded separate from observations about the user (stored in an Entity object), allowing for consistent retrieval, identification and easy manipulation according to user preferences.

## Planned Features/Upgrades

  1. Enhance Supabase integration: sync and optional tools implemented; consider read-side storage/cloud-first mode
  2. Fix Docker support
  3. Mobile device support
  4. Implement more robust search method(s)
  5. Upgrade visualizer:
     - Add editor functionality
     - Make look good
  6. Intimate but optional integration with Google suite products, and other brands
  7. Optimizations for usage across multiple devices
  8. Multi-profile/mult-user support
