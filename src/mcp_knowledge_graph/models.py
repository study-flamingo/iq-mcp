"""
Data models for the temporal knowledge graph memory system.

This module defines all the data structures used throughout the knowledge graph,
including entities, relations, and temporal observations with durability metadata.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field
from enum import Enum


class DurabilityType(str, Enum):
    """Enumeration of observation durability categories."""

    PERMANENT = "permanent"  # Never expires (e.g., "Born in 1990", "Has a degree in Physics")
    LONG_TERM = (
        "long-term"  # Relevant for 1+ years (e.g., "Works at Acme Corp", "Lives in New York")
    )
    SHORT_TERM = "short-term"  # Relevant for ~3 months (e.g., "Working on Project X", "Training for a marathon")
    TEMPORARY = "temporary"  # Relevant for ~1 month (e.g., "Currently learning TypeScript", "Traveling to Dominica")


class Observation(BaseModel):
    """
    Observation data model.

    Properties:
    - content(str): The observation content
    - timestamp(str): ISO date string when the observation was created
    - durability(DurabilityType): How long this observation is expected to remain relevant
    """

    content: str = Field(
        ..., title="Observation content", description="The observation content", alias="contents"
    )
    durability: DurabilityType = Field(
        ...,
        title="Durability",
        description="How long this observation is expected to remain relevant",
    )
    timestamp: str | None = Field(
        ...,
        title="Timestamp",
        description="ISO date string when the observation was created",
        alias="ts",
    )

    @classmethod
    def add_timestamp(
        cls, content: str, durability: DurabilityType = DurabilityType.SHORT_TERM
    ) -> "Observation":
        """Create a new timestamped observation from content and durability. The current datetime in ISO formatis used as the timestamp."""
        return cls(content=content, timestamp=datetime.now().isoformat(), durability=durability)


class Entity(BaseModel):
    """
    Primary nodes in the knowledge graph.

    Entites can be anything, and are arbitrary. When possible they should be concrete objects, people, events, or ideas, or groups of these.

    Each entity has a unique name, type classification (arbitrary), and list of timestamped observations with durability metadata. Example:

    - This is John: {'name': 'John Doe', 'entity_type': 'person', 'observations': [{'content': 'John Doe is a software engineer', 'durability': 'permanent', 'timestamp': '2025-01-01T00:00:00Z'}]}
    - This is Karen: {'name': 'Karen Smith', 'entity_type': 'person', 'observations': [{'content': 'Karen Smith is a very rude person', 'durability': 'permanent', 'timestamp': '2025-01-01T00:00:00Z'}]}

    Entities are connected to one another by Relations. Example:

    - John and Karen are paternal twins: {'from': 'John Doe', 'to': 'Karen Smith', 'relation_type': 'paternal twin'}
    - John and Karen are lifelong enemies and rivals: {'from': 'John Doe', 'to': 'Karen Smith', 'relation_type': 'evil twin'}

    Relations are stored in active voice and describe how entities interact or relate to each other.
    """

    name: str = Field(
        ...,
        title="Entity name",
        description="Unique identifier for the entity",
        alias="entity_name",
    )
    entity_type: str = Field(
        ...,
        title="Entity type",
        description="Type classification (e.g., 'person', 'organization', 'event')",
        alias="entityType",
    )
    observations: list[Observation] = Field(
        default_factory=list,
        title="List of observations",
        description="Associated observations with content, durabiltiy, and timestamp",
        alias="observation",
    )
    aliases: list[str] = Field(
        default_factory=list,
        title="Aliases",
        description="Alternative names for the entity that should resolve to this entity",
        alias="alias",
    )

    class Config:
        populate_by_name = True


class Relation(BaseModel):
    """
    Directed connections between entities.

    Relations are stored in active voice and describe how entities
    interact or relate to each other.
    """

    from_entity: str = Field(
        ..., title="From entity", description="Source entity name", alias="from"
    )
    to_entity: str = Field(..., title="To entity", description="Target entity name", alias="to")
    relation_type: str = Field(
        ...,
        title="Relation type",
        description="Relationship type in active voice. Example: (A) is really interested in (B)",
        alias="relationType",
    )

    class Config:
        populate_by_name = True


class KnowledgeGraph(BaseModel):
    """
    Complete knowledge graph containing entities and their relations.

    This is the top-level container for the entire memory system,
    supporting both entities and the relations between them.

    The memory system is comprised of two core components: entities and relations. Each posess a number
    of properties:

    Entities:
        - name: Entity name
        - entity_type: Entity type
        - observations: List of observations (Observation objects)
        - aliases: List of alternative names for the entity that should resolve to this entity

    Relations are directed connections between entities. They are stored in active voice and
    describe how entities interact or relate to each other.

    Relations:
        - from_entity: Source entity name
        - to_entity: Target entity name
        - relation_type: Relationship type in active voice. Example: (A) is really interested in (B)

    Observations are timestamped statements about entities. They are used to track the state of entities over time.

    Observations are nested within entities, and themselves have the following properties:
        - content: Observation content
        - durability: How long this observation is expected to remain relevant
        - timestamp: ISO date string when the observation was created (added automatically by the manager)

    Entities are the nodes in the graph, and relations are the edges.

    Entities are arbitrary and can represent anything, but ideally they represent a concrete object,
    person, event, or idea.




    """

    entities: list[Entity] = Field(
        default_factory=list, title="Entities", description="All entities in the knowledge graph"
    )
    relations: list[Relation] = Field(
        default_factory=list, title="Relations", description="All relations between entities"
    )


class CleanupResult(BaseModel):
    """Result of cleaning up outdated observations."""

    entities_processed_count: int = Field(
        ...,
        title="Number of entities processed",
        description="Number of entities that were processed",
    )
    observations_removed_count: int = Field(
        ...,
        title="Number of observations removed",
        description="Total number of observations removed",
    )
    removed_observations: list[dict] = Field(
        default_factory=list,
        title="Removed observations",
        description="Details of removed observations",
    )


class DurabilityGroupedObservations(BaseModel):
    """Observations grouped by their durability type."""

    permanent: list[Observation] = Field(
        default_factory=list,
        title="Permanent observations",
        description="Observations with durability type 'permanent'",
    )
    long_term: list[Observation] = Field(
        default_factory=list,
        title="Long-term observations",
        description="Observations with durability type 'long-term'",
    )
    short_term: list[Observation] = Field(
        default_factory=list,
        title="Short-term observations",
        description="Observations with durability type 'short-term'",
    )
    temporary: list[Observation] = Field(
        default_factory=list,
        title="Temporary observations",
        description="Observations with durability type 'temporary'",
    )


class ObservationRequest(BaseModel):
    """Request model for managing observations for an entity in the knowledge graph. Used for both addition and deletion."""

    entity_name: str = Field(
        ...,
        title="Entity name",
        description="The name of the entity to add observations to",
        alias="entityName",
    )
    observations: list[Observation] = Field(
        ...,
        title="Observations",
        description="Observations to add - objects with durability metadata",
        alias="observation",
    )
    confirm: bool | None = Field(
        ...,
        title="Confirm",
        description="Optional confirmation property. Must be passed for certain sensitive operations. ***ALWAYS VERIFY WITH THE USER BEFORE SETTING TO TRUE*** Experimental.",
        alias="verify",
    )


class AddObservationResult(BaseModel):
    """Result of adding observations to an entity."""

    entity_name: str = Field(
        ..., title="Entity name", description="The entity name that was updated", alias="entityName"
    )
    added_observations: list[Observation] = Field(
        ...,
        title="Added observations",
        description="The observations that were actually added (excluding duplicates)",
        alias="observation",
    )


class DeleteObservationRequest(BaseModel):
    """Request model for deleting observations from an entity."""

    entity_name: str = Field(
        ...,
        title="Entity name",
        description="The name of the entity containing the observations",
        alias="entityName",
    )
    observations: list[str] = Field(
        ...,
        title="Observations",
        description="Array of observation contents to delete",
        alias="observation",
    )


class DeleteEntryRequest(BaseModel):
    """Request model used to delete data from the knowledge graph.

    Properties:
        - 'entry_type' (str): must be one of: 'observation', 'entity', or 'relation'
        - 'data' (list[AddObservationRequest] | list[str] | list[Relation]): must be a list of the appropriate object for each entry_type:
            - entry_type = 'entity': list of entity names
            - entry_type = 'observation': [{entity_name, [observation content]}]
            - entry_type = 'relation': [{from_entity, to_entity, relation_type}]
    """

    entry_type: Literal["observation", "entity", "relation"] = Field(
        description="Type of entry to create: 'observation', 'entity', or 'relation'"
    )
    data: list[ObservationRequest] | list[str] | list[Relation] | None = Field(
        description="""A list of the appropriate object for the given entry_type.
        
        - entry_type = 'entity': list of entity names
        - entry_type = 'observation': list of DeleteObservationRequest objects
        - entry_type = 'relation': list of Relation objects
        """
    )


class CreateEntryRequest(BaseModel):
    """Request model used to validate and add data to the knowledge graph.

    Properties:
        - 'entry_type' (str): must be one of: 'observation', 'entity', or 'relation'
        - 'data' (list[AddObservationRequest] | list[Entity] | list[Relation])

    'data' must be a list of the appropriate object for each entry_type:

        - observation: [{'entity_name': 'entity_name', 'content': list[{'content':'observation_content', 'durability': Literal['temporary', 'short-term', 'long-term', 'permanent']}]}]  (timestamp will be automatically added)
        - entity: [{'name': 'entity_name', 'entity_type': entity type, 'observations': [{'content': str, 'durability': Literal['temporary', 'short-term', 'long-term', 'permanent']}]}]
        - relation: [{'from': 'entity_name', 'to': 'entity_name', 'relation_type': 'relation_type'}]
    """

    entry_type: Literal["observation", "entity", "relation"] = Field(
        description="Type of entry to create: 'observation', 'entity', or 'relation'"
    )
    data: list[ObservationRequest] | list[Entity] | list[Relation] = Field(
        description="""Data to be added to the knowledge graph. Expected format depends on the entry_type:
        
        - observation: list of AddObservationRequest objects
        - entity: list of Entity objects
        - relation: list of Relation objects
        """
    )
