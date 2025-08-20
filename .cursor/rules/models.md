# Model cheat sheet for [[src/mcp_knowledge_graph/models.py]]

Generated overview to remember data model structures and track changes. Keep this in sync when updating the models.

## Diagrams

```mermaid
classDiagram
    direction TB

    class DurabilityType {
        <<enumeration>>
        PERMANENT
        LONG_TERM
        SHORT_TERM
        TEMPORARY
    }

    class Observation {
        +str content (alias: contents)
        +DurabilityType durability
        +str|None timestamp (alias: ts)
        +add_timestamp(content: str, durability: DurabilityType) Observation
    }

    class Entity {
        +str name (alias: entity_name)
        +str entity_type (alias: entityType)
        +list~Observation~ observations (alias: observation)
        +list~str~ aliases (alias: alias)
    }

    class Relation {
        +str from_entity (alias: from)
        +str to_entity (alias: to)
        +str relation_type (alias: relationType)
    }

    class KnowledgeGraph {
        +list~Entity~ entities
        +list~Relation~ relations
    }

    Entity "1" o-- "*" Observation : observations
    KnowledgeGraph "1" --> "*" Entity : entities
    KnowledgeGraph "1" --> "*" Relation : relations
    Observation --> DurabilityType
```

```mermaid
classDiagram
    direction TB

    class CleanupResult {
        +int entities_processed_count
        +int observations_removed_count
        +list~dict~ removed_observations
    }

    class DurabilityGroupedObservations {
        +list~Observation~ permanent
        +list~Observation~ long_term
        +list~Observation~ short_term
        +list~Observation~ temporary
    }

    class AddObservationResult {
        +str entity_name (alias: entityName)
        +list~Observation~ added_observations (alias: observation)
    }
```

```mermaid
classDiagram
    direction TB

    class ObservationRequest {
        +str entity_name (alias: entityName)
        +list~Observation~ observations (alias: observation)
        +bool|None confirm (alias: verify)
    }

    class DeleteObservationRequest {
        +str entity_name (alias: entityName)
        +list~str~ observations (alias: observation)
    }

    class CreateEntryRequest {
        +Literal("observation","entity","relation") entry_type
        +list[data] data
    }

    class DeleteEntryRequest {
        +Literal("observation","entity","relation") entry_type
        +list[data]|None data
    }

    %% Notes to clarify union types for request.data
    note for CreateEntryRequest "When entry_type=='observation': list~ObservationRequest~\nWhen 'entity': list~Entity~\nWhen 'relation': list~Relation~"

    note for DeleteEntryRequest "When entry_type=='entity': list~str~ (entity names)\nWhen 'observation': list~DeleteObservationRequest~\nWhen 'relation': list~Relation~"

    ObservationRequest --> Observation
    DeleteObservationRequest --> Observation : by content
    CreateEntryRequest --> Entity
    CreateEntryRequest --> ObservationRequest
    CreateEntryRequest --> Relation
    DeleteEntryRequest --> Relation
```

### Quick reference (fields and aliases)

- **DurabilityType**: `permanent`, `long-term`, `short-term`, `temporary`.
- **Observation**:
  - **content**: `str` (alias: `contents`)
  - **durability**: `DurabilityType`
  - **timestamp**: `str | None` (alias: `ts`)
  - Classmethod: `add_timestamp(content, durability)` → `Observation`
- **Entity**:
  - **name**: `str` (alias: `entity_name`)
  - **entity_type**: `str` (alias: `entityType`)
  - **observations**: `list[Observation]` (alias: `observation`)
  - **aliases**: `list[str]` (alias: `alias`)
- **Relation**:
  - **from_entity**: `str` (alias: `from`)
  - **to_entity**: `str` (alias: `to`)
  - **relation_type**: `str` (alias: `relationType`)
- **KnowledgeGraph**:
  - **entities**: `list[Entity]`
  - **relations**: `list[Relation]`
- **CleanupResult**:
  - **entities_processed_count**: `int`
  - **observations_removed_count**: `int`
  - **removed_observations**: `list[dict]`
- **DurabilityGroupedObservations**:
  - **permanent/long_term/short_term/temporary**: `list[Observation]`
- **ObservationRequest**:
  - **entity_name**: `str` (alias: `entityName`)
  - **observations**: `list[Observation]` (alias: `observation`)
  - **confirm**: `bool | None` (alias: `verify`)
- **AddObservationResult**:
  - **entity_name**: `str` (alias: `entityName`)
  - **added_observations**: `list[Observation]` (alias: `observation`)
- **DeleteObservationRequest**:
  - **entity_name**: `str` (alias: `entityName`)
  - **observations**: `list[str]` (alias: `observation`)
- **CreateEntryRequest**:
  - **entry_type**: `Literal["observation","entity","relation"]`
  - **data**: depends on `entry_type`:
    - `observation`: `list[ObservationRequest]`
    - `entity`: `list[Entity]`
    - `relation`: `list[Relation]`
- **DeleteEntryRequest**:
  - **entry_type**: `Literal["observation","entity","relation"]`
  - **data**: depends on `entry_type` (or `None` permitted):
    - `entity`: `list[str]` (entity names)
    - `observation`: `list[DeleteObservationRequest]`
    - `relation`: `list[Relation]`

### Maintenance tips

- When you add/change a field, alias or class in `src/mcp_knowledge_graph/models.py`, update both the Mermaid diagrams and the Quick reference above.
- Prefer keeping property names and aliases consistent across request/response models.
- For big refactors, add a dated note here describing the change at a high level.
