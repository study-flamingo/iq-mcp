"""
Data models for the temporal knowledge graph memory system.

This module defines all the data structures used throughout the knowledge graph,
including entities, relations, and temporal observations with durability metadata.
"""

from datetime import datetime, timezone
from typing import Literal
import uuid
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from .settings import Logger as logger


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

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )
    content: str = Field(..., title="Observation content", description="The observation content")
    durability: DurabilityType = Field(
        ...,
        title="Durability",
        description="How long this observation is expected to remain relevant",
    )
    timestamp: datetime | None = Field(
        ...,
        title="Timestamp",
        description="ISO date string when the observation was created",
    )

    @classmethod
    def add_timestamp(
        cls, content: str, durability: DurabilityType = DurabilityType.SHORT_TERM
    ) -> "Observation":
        """Create a new timestamped observation from content and durability. The current datetime in ISO format (UTC) is used as the timestamp."""
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return cls(content=content, timestamp=ts, durability=durability)

    def __repr__(self):
        return f"Observation(content={self.content}, timestamp={self.timestamp}, durability={self.durability})"


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

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )
    id: str = Field(
        ...,
        default_factory=lambda: str(uuid.uuid4()),
        title="Entity ID",
        description="Unique identifier for the entity",
    )
    name: str = Field(
        ...,
        title="Entity name",
        description="The canonical name of the entity",
    )
    entity_type: str = Field(
        ...,
        title="Entity type",
        description="Type classification (e.g., 'person', 'organization', 'event')",
    )
    observations: list[Observation] = Field(
        default_factory=list,
        title="List of observations",
        description="Associated observations with content, durabiltiy, and timestamp",
    )
    aliases: list[str] = Field(
        default_factory=list,
        title="Aliases",
        description="Alternative names for the entity",
    )
    icon: str | None = Field(
        default="👤",
        title="Icon",
        description="Emoji used to represent the entity in certain contexts",
    )

    def __repr__(self):
        return f"Entity(name={self.name}, entity_type={self.entity_type}, observations={self.observations}, aliases={self.aliases}, icon={self.icon})"


class Relation(BaseModel):
    """
    Directed connections between entities.

    Relations are stored in active voice and describe how entities
    interact or relate to each other.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )
    from_entity: str | None = Field(
        ..., deprecated=True, title="From entity", description="Source entity name"
    )
    to_entity: str | None = Field(..., title="To entity", description="Target entity name")
    relation_type: str = Field(
        ...,
        title="Relation type",
        description="Relationship type in active voice. Example: (A) is really interested in (B)",
    )
    from_id: str | None = Field(
        default=None,
        title="From entity ID",
        description="Unique identifier for the source entity",
    )
    to_id: str | None = Field(
        default=None,
        title="To entity ID",
        description="Unique identifier for the target entity",
    )

    def __repr__(self):
        return f"Relation(from_entity={self.from_entity}, to_entity={self.to_entity}, relation_type={self.relation_type})"


class UserIdentifier(BaseModel):
    """
    Identifier to pair the user with '__default_user__' in the knowledge graph.

    Fields:
      - preferred_name: The preferred name of the user. Preferred name is prioritized over other
        names for the user. If not provided, one will be selected from the other provided names in
        the following fallback order:
          1. Nickname
          2. Prefix + First name
          3. First name
          4. Last name
      - first_name: The given name of the user
      - last_name: The family name of the user
      - middle_names: The middle names of the user
      - pronouns: The pronouns of the user
      - nickname: The nickname of the user
      - prefixes: The prefixes of the user
      - suffixes: The suffixes of the user
      - emails: The email addresses of the user
      - base_name: The base name of the user - first, middle, and last name without any prefixes or suffixes. Organized as a list of strings with each part.
      - names: Various full name forms for the user, depending on the provided information. Index 0 is the first, middle, and last name without any prefixes or suffixes.
    """

    linked_entity_id: str | None = Field(
        default=None,
        title="Linked entity ID",
        description="The ID of the entity that is linked to the user. This entity will be used to store observations about the user.",
    )
    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )
    preferred_name: str | None = Field(
        default=None,
        title="Preferred name",
        description="The preferred name of the user",
    )
    first_name: str | None = Field(
        default=None,
        title="First name",
        description="The given name of the user",
    )
    last_name: str | None = Field(
        default=None,
        title="Last name",
        description="The family name of the user",
    )
    middle_names: list[str] | None = Field(
        default=None,
        title="Middle names",
        description="The middle names of the user",
    )
    pronouns: str | None = Field(
        default=None,
        title="Pronouns",
        description="The pronouns of the user. Example: he/him, she/her, they/them, etc.",
    )
    nickname: str | None = Field(
        default=None,
        title="Nickname",
        description="The nickname of the user",
    )
    prefixes: list[str] | None = Field(
        default=None,
        title="Prefixes",
        description="The prefixes of the user. Example: Mrs., Mr., Dr., Sgt., etc.",
    )
    suffixes: list[str] | None = Field(
        default=None,
        title="Suffixes",
        description="The suffixes of the user. Example: Jr., Sr., II, III, etc.",
    )
    emails: list[str] | None = Field(
        default=None,
        title="Email",
        description="The email of the user",
    )
    base_name: list[str] | None = Field(
        default=None,
        title="Base name",
        description="The base name of the user - first, middle, and last name without any prefixes or suffixes. Organized as a list of strings with each part.",
    )
    names: list[str] = Field(
        ...,
        title="Full name",
        description="Various full name forms for the user, depending on the provided information. Index 0 is the first, middle, and last name without any prefixes or suffixes.",
    )
    linked_entity: Entity | None = Field(
        default=None,
        title="Linked entity",
        description="The entity that is linked to the user. This is used to link the user to the entity that represents them in the knowledge graph.",
    )

    def __repr__(self):
        return f"UserIdentifier(preferred_name={self.preferred_name}, first_name={self.first_name}, last_name={self.last_name}, middle_names={self.middle_names}, pronouns={self.pronouns}, nickname={self.nickname}, prefixes={self.prefixes}, suffixes={self.suffixes}, emails={self.emails}, base_name={self.base_name}, names={self.names})"

    @classmethod
    def from_llm(
        cls,
        preferred_name: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        middle_names: list[str] | None = None,
        pronouns: str | None = None,
        nickname: str | None = None,
        prefixes: list[str] | None = None,
        suffixes: list[str] | None = None,
        emails: list[str] | None = None,
    ) -> "UserIdentifier":
        """Create a UserIdentifier from a LLM response."""

        # Compute the preferred name
        if not preferred_name:
            if nickname:
                preferred_name = nickname
            elif prefixes:
                preferred_name = f"{prefixes[0]} {first_name}"
            elif first_name:
                preferred_name = first_name
            elif last_name:
                preferred_name = last_name
            else:
                raise ValueError("No suitable name provided for the user")

        # Compute the base name parts - first, middle(s), and last name without any prefixes or suffixes
        base_name_parts: list[str] = []
        if first_name:
            base_name_parts.append(first_name)
        if middle_names:
            base_name_parts.extend(middle_names)
        if last_name:
            base_name_parts.append(last_name)
        if not base_name_parts:
            raise ValueError("No suitable name provided for the user")

        # First index is first_name, last_name
        base_name_str = " ".join(base_name_parts)
        full_names = [base_name_str]
        # Next index is first_name, middle_names, last_name. Results in a duplicate if no middle names are provided.
        if middle_names:
            middle_joined = " ".join(middle_names)
            full_names.append(" ".join([n for n in [first_name, middle_joined, last_name] if n]))
        else:
            full_names.append(" ".join([n for n in [first_name, last_name] if n]))

        if len(full_names) != 2:
            raise ValueError("Unknown error occured during name computation")
        # Add all possible prefix/suffix combinations on top of the base name of the user
        if prefixes:
            for pfx in prefixes:
                prefixed_name = f"{pfx} {base_name_str}"
                full_names.append(prefixed_name)
                if suffixes:
                    for sfx in suffixes:
                        full_names.append(f"{prefixed_name}, {sfx}")

        return cls(
            first_name=first_name,
            last_name=last_name,
            middle_names=middle_names,
            base_name=base_name_parts,
            preferred_name=preferred_name,
            nickname=nickname,
            prefixes=prefixes,
            suffixes=suffixes,
            pronouns=pronouns,
            emails=emails,
            names=full_names,
        )

    @classmethod
    def from_default(cls) -> "UserIdentifier":
        """Create a default UserIdentifier."""
        return cls(
            first_name="__default_user__",
            last_name=None,
            middle_names=None,
            preferred_name=None,
            pronouns=None,
            nickname=None,
            prefixes=None,
            suffixes=None,
            emails=None,
            names=["__default_user__"],
        )


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

    The knowledge graph also contains information about the user, including their real/preferred name, pronouns,
    email addresses, and other information, provided by the user, throught the LLM. This information is optional,
    but aids the LLM in better understanding the user and their preferences.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )
    user_info: UserIdentifier = Field(
        ..., title="User info", description="Information about the user"
    )
    entities: list[Entity] | None = Field(
        default=None, title="Entities", description="All entities in the knowledge graph"
    )
    relations: list[Relation] | None = Field(
        default=None, title="Relations", description="All relations between entities"
    )

    def __repr__(self):
        return f"KnowledgeGraph(entities={self.entities}, relations={self.relations}, user_info={self.user_info})"

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        """Initialize the knowledge graph from a dictionary of values."""
        return cls(
            user_info=UserIdentifier(**data["user_info"]),
            entities=[Entity(**e) for e in data["entities"]],
            relations=[Relation(**r) for r in data["relations"]],
        )

    @classmethod
    def from_default(cls) -> "KnowledgeGraph":
        """Initialize the knowledge graph with default values."""
        return cls(
            user_info=UserIdentifier.from_default(),
            entities=[
                Entity(
                    name="__default_user__",
                    entity_type="__default_user__",
                    observations=[
                        Observation(
                            content="**Is the user you are speaking to**",
                            durability=DurabilityType.PERMANENT,
                            timestamp=datetime.now().isoformat(),
                        )
                    ],
                )
            ],
            relations=[],
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

    def __repr__(self):
        return f"CleanupResult(entities_processed_count={self.entities_processed_count}, observations_removed_count={self.observations_removed_count}, removed_observations={self.removed_observations})"


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

    def __repr__(self):
        return f"DurabilityGroupedObservations(permanent={self.permanent}, long_term={self.long_term}, short_term={self.short_term}, temporary={self.temporary})"


class ObservationRequest(BaseModel):
    """Request model for managing observations for an entity in the knowledge graph. Used for both addition and deletion."""

    entity_name: str = Field(
        ...,
        title="Entity name",
        description="The name of the entity to add observations to",
    )
    observations: list[Observation] = Field(
        ...,
        title="Observations",
        description="Observations to add - objects with durability metadata",
    )
    confirm: bool | None = Field(
        ...,
        title="Confirm",
        description="Optional confirmation property. Must be passed for certain sensitive operations. ***ALWAYS VERIFY WITH THE USER BEFORE SETTING TO TRUE*** Experimental.",
    )


class AddObservationResult(BaseModel):
    """Result of adding observations to an entity."""

    entity_name: str = Field(
        ..., title="Entity name", description="The entity name that was updated"
    )
    entity_icon: str | None = Field(
        default=None,
        title="Entity icon",
        description="The icon of the entity that was updated",
    )
    added_observations: list[Observation] = Field(
        ...,
        title="Added observations",
        description="The observations that were actually added (excluding duplicates)",
    )

    def __repr__(self):
        return f"AddObservationResult(entity_name={self.entity_name}, added_observations={self.added_observations})"


class DeleteObservationRequest(BaseModel):
    """Request model for deleting observations from an entity."""

    entity_name: str = Field(
        ...,
        title="Entity name",
        description="The name of the entity containing the observations",
    )
    observations: list[str] = Field(
        ...,
        title="Observations",
        description="Array of observation contents to delete",
    )

    def __repr__(self):
        return f"DeleteObservationRequest(entity_name={self.entity_name}, observations={self.observations})"


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


class CreateEntityResult(BaseModel):
    """Result of creating an entity."""

    entities: list[Entity] = Field(
        ...,
        title="Entities",
        description="The entities that were successfully created (excludes existing names)",
    )

    def __repr__(self):
        return f"CreateEntityResult(entities={self.entities})"


class CreateRelationResult(BaseModel):
    """Result of creating a relation."""

    relations: list[Relation] = Field(
        ...,
        title="Relations",
        description="The relations that were successfully created",
    )

    def __repr__(self):
        return f"CreateRelationResult(relations={self.relations})"
