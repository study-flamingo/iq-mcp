"""
Data models for the temporal knowledge graph memory system.

This module defines all the data structures used throughout the knowledge graph,
including entities, relations, and temporal observations with durability metadata.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict, field_validator
from enum import Enum
import regex as re
from .settings import Logger as logger, Settings


# Helper functions
_GRAPHEMES = re.compile(r"\X")
_HAS_EMOJI = re.compile(r"(\p{Extended_Pictographic}|\p{Regional_Indicator})")
def is_emoji(s: str) -> bool:
    """Check if a string is a valid emoji."""
    s = s.strip()
    g = _GRAPHEMES.findall(s)
    return len(g) == 1 and _HAS_EMOJI.search(g[0]) is not None

def validate_entity_id(id: str) -> str | None:
    """Validate the provided entity ID."""
    if (
        not id
        or not isinstance(id, str)
        or not id.strip()
        or len(id) != 8
        or not id.isalnum()
    ):
        logger.error(f"Invalid entity ID: {id}")
        return None
    return id

class KnowledgeGraphException(Exception):
    """Base exception for the knowledge graph."""
    pass


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
    content: str = Field(
        ...,
        title="Observation content", 
        description="The observation content. Should be a single sentence or concise statement in active voice. Example: 'John Doe is a software engineer'",
    )
    durability: DurabilityType = Field(
        ...,
        title="Durability",
        description="How long this observation is expected to remain relevant",
    )
    timestamp: datetime = Field(..., title="Timestamp", description="ISO date when the observation was created")

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

    - John and Karen are paternal twins: {'from': 'John Doe', 'to': 'Karen Smith', 'relation': 'paternal twin'}
    - John and Karen are lifelong enemies and rivals: {'from': 'John Doe', 'to': 'Karen Smith', 'relation': 'evil twin'}

    Relations are stored in active voice and describe how entities interact or relate to each other.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )
    id: str | None = Field(
        default=str(uuid4())[:8],
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
        description="Associated observations with content, durability, and timestamp",
    )
    aliases: list[str] = Field(
        default_factory=list,
        title="Aliases",
        description="Alternative names for the entity",
    )
    _icon: str | None = None

    @property
    def icon(self) -> str | None:
        """Return the icon of the entity if it exists, and its display is not disabled in settings."""
        if Settings.no_emojis or not self._icon:
            return None
        return self._icon

    @icon.setter
    def icon(self, icon: str):
        """Set the icon of the entity. Must be a single valid emoji."""
        self._icon = icon if is_emoji(icon) else None
        if not self._icon:
            logger.debug(f"Invalid emoji '{icon}' given for entity '{self.name}'")
            raise ValueError(f"Error setting icon for entity '{self.name}': value must be a single valid emoji. Instead, received '{icon}'")

    # def ensure_id(self) -> str:
    #     """
    #     Ensure that the ID is set. If not, generate a new one and assign it to the entity. Returns the ID.
        
    #     Will be deprecated at some point.
    #     """
    #     if not self.id:
    #         self.id = generate_entity_id()
    #     return self.id

    def to_dict(self) -> dict[str, Any]:
        """Return the entity as a JSON dictionary ensuring the ID is set."""
        self.ensure_id()
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_name(cls, name: str, entity_type: str) -> "Entity":
        """Create an entity from a given name and entity type."""
        return cls(name=name, entity_type=entity_type)

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """Initialize the entity from a dictionary of values. Ideal for reading from storage."""
        logger.debug(f"Loading entity from dictionary: {data}")

        for k in ["name", "entity_type"]:  # TODO: id will be required in the future
            v = data.get(k)
            if not isinstance(v, str) or not v.strip():
                raise ValueError(f"Missing or invalid required key: {k}")

        if not data.get("id"):
            logger.warning(f"Entity '{data['name']}' ID is missing, manager will generate a new one")
            data["id"] = None

        observations = [Observation(**o) for o in (data.get("observations") or [])]
        aliases = [str(a) for a in (data.get("aliases") or [])]

        e = cls(id=data["id"], name=data["name"], entity_type=data["entity_type"],
                observations=observations, aliases=aliases)
        icon = data.get("icon")
        if icon:
            e.icon = icon  # will validate via setter
        return e

    @classmethod
    def from_values(
        cls, 
        name: str, 
        entity_type: str,
        observations: list[Observation] | None = None,
        aliases: list[str] | None = None,
        icon: str | None = None,
        id: str | None = None
        ) -> "Entity":
        """
        Create an entity from values.
        
        Args:
            name (str, required): The name of the entity
            entity_type (str, required): The type of the entity
            observations (list[Observation]): The observations of the entity
            aliases (list[str]): The aliases of the entity
            icon (str): The emoji to provide a visual representation of the entity. Must be a single valid emoji.
            id (str): The unique identifier of the entity in the knowledge graph.
        
        The ID is managed by the KnowledgeGraphManager and one will be generated if it is not provided, i.e., if creating a new entity from values.

        Returns:
            Entity: The created entity
        """
        e = cls(name=name, entity_type=entity_type,
                observations=observations or [],
                aliases=aliases or [],
                icon=icon,
                id=id)
        if icon:
            if is_emoji(icon):
                e.icon = icon
            else:
                logger.warning(f"Invalid emoji '{icon}' given for new entity '{name}'")
        return e

class Relation(BaseModel):
    """
    Directed connections between entities.

    Relations are stored in active voice and describe how entities
    interact or relate to each other.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
        validate_by_alias=True,
    )

    from_entity: str | None = Field(
        default=None,
        title="From entity",
        description="Source entity name (in-memory convenience only; not persisted)",
    )
    to_entity: str | None = Field(
        default=None,
        title="To entity",
        description="Target entity name (in-memory convenience only; not persisted)",
    )
    from_id: str = Field(
        default=None,
        title="From entity ID",
        description="Unique identifier for the source entity",
    )
    relation: str = Field(
        ...,
        title="Relation type",
        description="Relationship content/description in active voice. Example: (A) is really interested in (B)",
        alias="relation_type",
    )
    to_id: str = Field(
        default=None,
        title="To entity ID",
        description="Unique identifier for the target entity",
    )

    @classmethod
    def from_entities(cls, from_entity: Entity, to_entity: Entity, relation: str) -> "Relation":
        """Create a relation from one entity object to another with the given relation content."""
        from_id = from_entity.id
        to_id = to_entity.id
        return cls(from_id=from_id, to_id=to_id, relation=relation)

    @classmethod
    def from_dict(cls, data: dict) -> "Relation":
        """Initialize the relation from a dictionary of values. Ideal for reading from storage.

        Supports both id-only records and legacy name-based records.
        """
        content = data.get("relation") or data.get("relation_type")
        if not content or not isinstance(content, str) or not content.strip():
            raise ValueError(f"Invalid relation content: {content!r}")

        # Prefer IDs if present
        from_id_raw = data.get("from_id")
        to_id_raw = data.get("to_id")
        from_id = validate_entity_id(from_id_raw) if from_id_raw else None
        to_id = validate_entity_id(to_id_raw) if to_id_raw else None

        # Accept legacy names; ids will be resolved later by the manager
        from_entity = data.get("from_entity") or data.get("from")
        to_entity = data.get("to_entity") or data.get("to")
        if not (from_id and to_id):
            if not isinstance(from_entity, str) or not from_entity.strip():
                raise ValueError("Missing relation endpoints: need valid from_id/to_id or legacy names")
            if not isinstance(to_entity, str) or not to_entity.strip():
                raise ValueError("Missing relation endpoints: need valid from_id/to_id or legacy names")

        return cls(
            from_entity=from_entity,
            to_entity=to_entity,
            from_id=from_id,
            to_id=to_id,
            relation=content,
        )

    # def ensure_ids(self) -> None:    # Deprecated, as IDs are now required
    #     """
    #     Ensure that the from_id and to_id are set. If not, pull from the from_entity and to_entity.
    #     If either entities are not correctly typed, raise an error.
    #     """
    #     if not self.from_id or not self.to_id:
    #         try:
    #             if not self.from_entity or not self.to_entity:
    #                 raise ValueError("Bad relation: from_entity or to_entity are invalid!")
    #             if not isinstance(self.from_entity, Entity) or not isinstance(self.to_entity, Entity):
    #                 raise ValueError("Bad relation: from_entity and to_entity must be Entity objects")
    #             self.from_entity.ensure_id()
    #             self.to_entity.ensure_id()
    #             self.from_id = self.from_entity.id
    #             self.to_id = self.to_entity.id
    #         except Exception as e:
    #             raise KnowledgeGraphException(f"Error ensuring entity IDs of relationship {self.relation}: {e}")
    
    def to_dict(self) -> dict[str, Any]:
        """Serialize the relation to a JSON-compatible dictionary.

        Includes endpoint names for backward compatibility, relation content (by alias), and
        optional IDs when available. Does not attempt to generate or infer IDs at this stage.
        """
        return self.model_dump(
            by_alias=True,
            exclude_none=True,
            include={"relation", "from_id", "to_id"},
        )

    def __str__(self):
        return f"Entity:{self.from_id} '{self.relation}' Entity:{self.to_id}"

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
    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )

    linked_entity_id: str | None = Field(
        default=None,
        title="Linked entity ID",
        description="The ID of the entity that is linked to the user. This entity will be used to store observations about the user.",
    )
    preferred_name: str = Field(
        default="",
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

    @classmethod
    def from_values(
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
        """Create a UserIdentifier from values.
        
        Args:
            preferred_name (str): The preferred name of the user
            first_name (str): The given name of the user
            last_name (str): The family name of the user
            middle_names (list[str]): The middle names of the user
            pronouns (str): The pronouns of the user
            nickname (str): The nickname of the user
            prefixes (list[str]): The prefixes of the user
            suffixes (list[str]): The suffixes of the user
            emails (list[str]): The email addresses of the user
        """

        # Compute the preferred name if not given
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
            # Use nickname if all else fails
            base_name_parts.append(nickname or preferred_name)  # For alt names list, prefer nickname over preferred name
            logger.warning("No suitable first/middle/last name(s) provided for the user, using nickname")

        # names[0] is first_name, last_name without any prefixes or suffixes
        base_name_str = " ".join(base_name_parts)
        full_names = [base_name_str]

        # names[1] is first_name, middle_names, last_name. Results in a duplicate of names[0] (intentional) if no middle names are provided.
        if middle_names:
            parts = [first_name]
            parts.extend(middle_names)
            parts.append(last_name)
            full_names.append(" ".join(parts))
        elif first_name or last_name:
            parts = [first_name, last_name]
            full_names.append(" ".join(parts))
        else:
            # If no other suitable name can be computed, use the base name again
            full_names.append(base_name_str)

        if len(full_names) != 2:
            raise ValueError(f"Unknown error occured during name computation (full_names length={len(full_names)}, expected 2)")
        
        # Next, add all possible prefix/suffix combinations on top of the base name (names[0]) of the user
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
        """Create and return a default UserIdentifier."""
        return cls(
            first_name="user",
            preferred_name="user",
            pronouns="they/them",
            names=["user", "user"],
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
        - relation: Relationship type in active voice. Example: (A) is really interested in (B)

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
        extra="forbid",
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

    @classmethod
    def from_dict(cls, data: dict) -> "KnowledgeGraph":
        """Initialize the knowledge graph from a dictionary of values."""
        return cls(
            user_info=UserIdentifier(**data["user_info"]),
            entities=[Entity(**e) for e in data["entities"]],
            relations=[Relation(**r) for r in data["relations"]],
        )

    @classmethod
    def from_components(cls, user_info: UserIdentifier, entities: list[Entity], relations: list[Relation]) -> "KnowledgeGraph":
        """Initialize the knowledge graph by passing in the user info object, entities lists, and relations lists."""
        return cls(
            user_info=user_info,
            entities=entities,
            relations=relations,
        )

    @classmethod
    def from_default(cls) -> "KnowledgeGraph":
        """Initialize the knowledge graph with default values."""
        from .seed_graph import build_initial_graph
        return build_initial_graph()

    def to_dict_list(self) -> list[dict]:
        """Return the knowledge graph as a list of dictionaries suitable for writing to a JSONL file."""
        result = [self.user_info.model_dump(exclude_none=True)]
        result.extend([e.model_dump(exclude_none=True) for e in (self.entities or [])])
        result.extend([r.model_dump(exclude_none=True) for r in (self.relations or [])])
        return result

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

class CreateEntityRequest(BaseModel):
    """
    Request model used to create an entity.
    
    Properties:
        name (str): The name of the new entity to create.
        entity_type (str): The type of the entity. Arbitrary, but should be a noun.
        observations (list[Observation]): The observations of the entity. Optional, but recommended.
        aliases (list[str]): Any alternative names for the entity
        icon (str): The icon of the entity. Must be a single valid emoji. Optional, but recommended.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
        validate_by_alias=True,
    )
    name: str = Field(
        ...,
        title="Entity name",
        description="The name of the new entity to create.",
    )
    entity_type: str = Field(
        ...,
        title="Entity type",
        description="The type of the entity. Arbitrary, but should be a noun.",
        alias="type",
    )
    observations: list[Observation] | None = Field(
        default=None,
        title="Observations",
        description="The observations of the entity. Optional, but recommended.",
    )
    aliases: list[str] | None = Field(
        default=None,
        title="Aliases",
        description="Any alternative names for the entity",
    )
    icon: str | None = Field(
        default=None,
        title="Icon",
        description="The icon of the entity. Must be a single valid emoji. Optional, but recommended.",
    )

class CreateRelationRequest(BaseModel):
    """Request model used to create a relation."""
    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )

    from_entity_id: str = Field(
        ...,
        title="Originating entity ID",
        description="The name of the entity to create a relation from",
    )
    to_entity_id: str = Field(
        ...,
        title="Destination entity ID",
        description="The id of the entity to create a relation to",
    )
    relation: str = Field(
        ...,
        title="Relation content",
        description="Description of the relation. Should be in active voice and concise. Example: 'is the father of'",
    )

    @field_validator("from_entity_id")
    def _validate_from_entity_id(cls, v: str) -> str:
        """Validate the provided originating entity ID."""
        if v == "user":
            return v
        elif (
            not v
            or v == ""
            or not isinstance(v, str)
            or not v.strip()
            or len(v) != 8
            or not v.isalnum()
        ):
            raise ValueError(f"Invalid originating entity ID: {v}")
        return v

    @field_validator("to_entity_id")
    def _validate_to_entity_id(cls, v: str) -> str:
        """Validate the provided destination entity ID."""
        if v == "user":
            return v
        elif (
            not v
            or v == ""
            or not isinstance(v, str)
            or not v.strip()
            or len(v) != 8
            or not v.isalnum()
        ):
            raise ValueError(f"Invalid destination entity ID: {v}")
        return v

    @classmethod
    def from_objects(
        cls,
        from_entity: Entity,
        to_entity: Entity,
        relation: str,
    ) -> "CreateRelationRequest":
        """Produce a CreateRelationRequest from Entity objects and relation content."""
        if not (isinstance(from_entity, Entity) and from_entity.id):
            from_entity.ensure_id()
        if not (isinstance(to_entity, Entity) and to_entity.id):
            to_entity.ensure_id()
        return cls(from_entity_id=from_entity.id, to_entity_id=to_entity.id, relation=relation)

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
            - entry_type = 'relation': [{from_entity, to_entity, relation}]
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
        - 'data' (list[ObservationRequest] | list[Entity] | list[Relation])

    'data' must be a list of the appropriate object for each entry_type:

        - observation: [{'entity_name': 'entity_name', 'content': list[{'content':'observation_content', 'durability': Literal['temporary', 'short-term', 'long-term', 'permanent']}]}]  (timestamp will be automatically added)
        - entity: [{'name': 'entity_name', 'entity_type': entity type, 'observations': [{'content': str, 'durability': Literal['temporary', 'short-term', 'long-term', 'permanent']}]}]
        - relation: [{'from': 'entity_name', 'to': 'entity_name', 'relation': 'relation'}]
    """
    model_config = ConfigDict(
        deprecated=True,
        populate_by_name=True,
        validate_by_name=True,
    )
    entry_type: Literal["observation", "entity", "relation"] = Field(
        description="Type of entry to create: 'observation', 'entity', or 'relation'"
    )
    data: list[ObservationRequest] | list[Entity] | list[Relation] = Field(
        description="""Data to be added to the knowledge graph. Expected format depends on the entry_type:
        
        - observation: list of ObservationRequest objects
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

class CreateRelationResult(BaseModel):
    """Result of creating a relation."""

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )
    relations: list[Relation] = Field(
        ...,
        title="Relations",
        description="The relations that were successfully created",
    )
