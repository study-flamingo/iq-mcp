"""
Data models for the temporal knowledge graph memory system.

This module defines all the data structures used throughout the knowledge graph,
including entities, relations, and temporal observations with durability metadata.
"""

from datetime import datetime, timezone
from typing import Any, Literal, Annotated
from uuid import uuid4
from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
    computed_field,
    AliasChoices,
)
from enum import Enum
import regex as re
from .iq_logging import logger
from .settings import settings
from .settings import IQ_MCP_VERSION, IQ_MCP_SCHEMA_VERSION

# Helper functions
_GRAPHEMES = re.compile(r"\X")
_HAS_EMOJI = re.compile(r"(\p{Extended_Pictographic}|\p{Regional_Indicator})")


def is_emoji(s: str) -> bool:
    """Check if a string is a valid emoji."""
    s = s.strip()
    g = _GRAPHEMES.findall(s)
    return len(g) == 1 and _HAS_EMOJI.search(g[0]) is not None


def get_current_datetime() -> datetime:
    """Get the current datetime (UTC)."""
    return datetime.now(timezone.utc)


def validate_id_simple(id: str) -> str:
    """Simple validation of the provided entity ID. Checks if the ID is a string, is not empty, is 8 characters long, and is alphanumeric. If invalid, raises a ValueError."""
    if not id or not isinstance(id, str) or not id.strip() or len(id) != 8 or not id.isalnum():
        raise ValueError(f"Invalid entity ID found: {id}")
    return id


# Constrained ID type for entity/relation IDs (8-char alphanumeric)
EntityID = Annotated[
    str, Field(min_length=8, max_length=8, pattern=r"^[A-Za-z0-9]{8}$", strict=True)
]


class KnowledgeGraphException(Exception):
    """
    Base exception for the knowledge graph.

    KnowledgeGraphException should be raised when there is an issue involving interactions between
    elements or components of the knowledge graph.
    - Exceptions involving data validity should be raised as a `ValueError` instead.
    - More dangerous exceptions that do not involve data validity or typing (e.g., for logic that may compromise data integrity, involving loading/saving, edge cases, etc.) should be raised as a `RuntimeError` instead.
    """

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
    - durability(DurabilityType): How long this observation is expected to remain relevant
    - timestamp(datetime): Timestamp of when the observation was created
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
        default=DurabilityType.SHORT_TERM,
        title="Durability",
        description="How long this observation is expected to remain relevant",
    )
    timestamp: datetime = Field(
        default_factory=get_current_datetime,
        title="Timestamp",
        description="Timestamp of when the observation was created",
    )

    @classmethod
    def from_dict(cls, data: dict) -> "Observation":
        """Create a new timestamped observation from content and durability. The current datetime in ISO format (UTC) is used as the timestamp."""

        content = data.get("content")
        durability = data.get("durability", DurabilityType.SHORT_TERM)
        timestamp = data.get("timestamp") or get_current_datetime()
        return cls(content=content, timestamp=timestamp, durability=durability)

    @classmethod
    def from_values(
        cls,
        content: str,
        durability: DurabilityType = DurabilityType.SHORT_TERM,
        timestamp: datetime | str | None = None,
    ) -> "Observation":
        """Create a new timestamped observation from content and durability. If not provided, the current datetime in UTC is used as the timestamp."""
        if not timestamp:
            timestamp = datetime.now(timezone.utc)
        elif isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(content=content, durability=durability, timestamp=timestamp)

    # Timestamp defaults are handled by default_factory and pydantic parsing

    def save(self) -> dict:
        """Convert the observation to a dictionary for writing to storage."""
        record = self.model_dump()
        return record

    def __str__(self) -> str:
        """Return the observation content."""
        return f"{self.content}"

    def __eq__(self, other: "Observation") -> bool:
        """Check if the observation is equal to another observation."""
        return self.content == other.content and self.durability == other.durability

    @property
    def age(self) -> int:
        """Get the age of the observation in days."""
        ts = self.timestamp.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return (now - ts).days

    def is_outdated(self) -> bool:
        """
        Check if an observation is outdated based on durability and age.

        Args:
            obs: The observation to check

        Returns:
            True if the observation should be considered outdated, False otherwise.
        """
        try:
            days_old = self.age
        except Exception as e:
            raise ValueError(f"Error calculating age of observation: {e}")

        if self.durability == DurabilityType.PERMANENT:
            return False  # Never outdated
        elif self.durability == DurabilityType.LONG_TERM:
            return days_old > 365  # 1+ years old
        elif self.durability == DurabilityType.SHORT_TERM:
            return days_old > 90  # 3+ months old
        elif self.durability == DurabilityType.TEMPORARY:
            return days_old > 30  # 1+ month old
        else:
            return False


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
        validate_by_alias=True,
    )
    id: EntityID = Field(
        default_factory=lambda: str(uuid4())[:8],
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
    icon: str | None = Field(
        default=None,
        title="Icon",
        description="The emoji to provide a visual representation of the entity. Must be a single valid emoji.",
    )
    ctime: datetime = Field(
        default_factory=get_current_datetime,
        title="Creation time",
        description="The time the entity was created, in UTC",
    )
    mtime: datetime = Field(
        default_factory=get_current_datetime,
        title="Modification time",
        description="The time the entity was last modified, in UTC",
    )

    @staticmethod
    def update_mtime(entity: "Entity") -> None:
        """Update the modification timestamp of the entity to the current time in UTC."""
        entity.mtime = get_current_datetime()

    @field_validator("icon", mode="after")
    @classmethod
    def validate_icon(cls, v: str) -> str:
        """Set the icon of the entity. Must be a single valid emoji."""
        if v == "" or v is None:
            return ""
        elif is_emoji(v):
            return v
        else:
            raise ValueError(
                f"Error setting icon for entity '{cls.name}': value must be a single valid emoji. Instead, received '{v}'"
            )

    def icon_(self) -> str:
        """Return the icon of the entity if it exists and its display is not disabled in settings, plus a single whitespace. Otherwise, return an empty string."""
        if settings.no_emojis or not self.icon:
            return ""
        return self.icon + " "

    def to_dict(self) -> dict[str, Any]:
        """Return the entity as a JSON dictionary. Ideal for writing to storage."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
        """Initialize the entity from a dictionary of values. Ideal for loading from storage."""

        for k in ["name", "entity_type", "id"]:
            v = data.get(k, None)
            if not isinstance(v.strip(), str) or not v.strip():
                raise ValueError(f"Missing or invalid required key: {k}")

        observations = [Observation(**o) for o in (data.get("observations") or [])]
        aliases = [str(a) for a in (data.get("aliases") or [])]

        e = cls(
            id=data["id"],
            name=data["name"],
            entity_type=data["entity_type"],
            observations=observations,
            aliases=aliases,
            icon=data.get("icon", ""),
        )
        return e

    @classmethod
    def from_values(
        cls,
        name: str,
        entity_type: str,
        observations: list[Observation] | None = None,
        aliases: list[str] | None = None,
        icon: str | None = None,
        id: EntityID | None = None,
        ctime: datetime | str | None = None,
        mtime: datetime | str | None = None,
    ) -> "Entity":
        """
        Create an entity from values.

        Args:
            id (str): The unique identifier of the entity in the knowledge graph. Should be generated by the KnowledgeGraphManager.
            name (str, required): The name of the entity
            entity_type (str, required): The type of the entity
            observations (list[Observation]): The observations of the entity
            aliases (list[str]): The aliases of the entity
            icon (str): The emoji to provide a visual representation of the entity. Must be a single valid emoji.
            ctime (datetime): The timestamp when the entity was created (default: now, in UTC)
            mtime (datetime): The timestamp when the entity was last modified (default: now, in UTC)

        The ID is managed by the KnowledgeGraphManager and one will be generated if it is not provided, i.e., if creating a new entity from values.

        Returns:
            Entity: The created entity
        """
        if icon:
            if is_emoji(icon):
                pass
            else:
                logger.warning(f"Invalid emoji '{icon}' given for new entity '{name}'")
                icon = None

        if not ctime:
            ctime = datetime.now(timezone.utc)
        elif isinstance(ctime, str):
            ctime = datetime.fromisoformat(ctime)
        if not mtime:
            mtime = datetime.now(timezone.utc)
        elif isinstance(mtime, str):
            mtime = datetime.fromisoformat(mtime)

        return cls(
            id=id,
            name=name,
            entity_type=entity_type,
            observations=observations or [],
            aliases=aliases or [],
            icon=icon,
            ctime=ctime,
            mtime=mtime,
        )

    def cleanup_observations(self) -> "Entity":
        """
        Remove outdated and duplicate observations from the entity. Returns the clean entity.
        """
        # Prune outdated observations
        valid_observations = []
        for obs in self.observations:
            if not obs.is_outdated():
                valid_observations.append(obs)
            else:
                continue
        # Prune duplicate observations
        seen_observations: set[str] = set()
        was_pruned = False
        for o in valid_observations:
            content = o.content
            if content in seen_observations:
                valid_observations.remove(o)
                was_pruned = True
            else:
                seen_observations.add(content)

        if was_pruned:
            logger.debug(f"Cleaned up observations for entity {self.name} ({self.id})")
        self.observations = valid_observations
        return self


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
        deprecated=True,
        title="From entity",
        description="Source entity name (in-memory convenience only; not persisted)",
    )
    to_entity: str | None = Field(
        default=None,
        deprecated=True,
        title="To entity",
        description="Target entity name (in-memory convenience only; not persisted)",
    )
    from_id: EntityID = Field(
        title="From entity ID",
        description="Unique identifier for the source entity",
    )
    relation: str = Field(
        ...,
        title="Relation type",
        description="Relationship content/description in active voice. Example: (A) is really interested in (B)",
        validation_alias=AliasChoices("relation", "relation_type", "content"),
    )
    to_id: EntityID = Field(
        title="To entity ID",
        description="Unique identifier for the target entity",
    )
    ctime: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        title="Created at",
        description="Timestamp when the relation was created",
        alias="created_at",
    )

    @classmethod
    def from_entities(cls, from_entity: Entity, to_entity: Entity, relation: str) -> "Relation":
        """Create a relation from one entity object to another with the given relation content."""
        from_id = from_entity.id
        to_id = to_entity.id
        return cls(from_id=from_id, to_id=to_id, relation=relation)

    @classmethod
    def from_dict(cls, data: dict) -> "Relation":
        """Initialize the relation from a dictionary of values. Ideal for reading from storage."""
        content = (
            data.get("relation") or data.get("content") or data.get("relation_type")
        )  # compat with old data format
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Relation content invalid or missing")
        return cls(
            from_id=data.get("from_id"),
            to_id=data.get("to_id"),
            relation=content,
        )

    @classmethod
    def from_values(
        cls, from_id: EntityID, to_id: EntityID, relation: str, ctime: datetime = None
    ) -> "Relation":
        """
        Create a relation from individual values.

        Args:
          - `from_id`: The ID of the originating entity
          - `to_id`: The ID of the destination entity
          - `relation`: The relation content
          - `ctime` (optional): The timestamp when the relation was created (default: now, in UTC)
        """

        if ctime is None:
            ctime = datetime.now(timezone.utc)
        return cls(from_id=from_id, to_id=to_id, relation=relation, ctime=ctime)

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
    Unique object representing the user and their identity in the knowledge graph. Also links the
    uyser to the user-linked entity in the knowledge graph.

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

    The following fields are computed automatically from the provided information, and should not be provided:
      - base_name: The base name of the user - first, middle, and last name without any prefixes or suffixes. Organized as a list of strings with each part.
      - names: Various full name forms for the user, depending on the provided information. Index 0 is the first, middle, and last name without any prefixes or suffixes.
      - linked_entity_id: The ID of the entity that is linked to the user. This entity will be used to store observations about the user.

    Constructors:
      - from_values(): Create a UserIdentifier from individually-provided fields.
      - from_default(): Create a UserIdentifier with the default values.
      - from_dict(data: dict): Initialize the UserIdentifier from a dictionary containing the above fields.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )

    linked_entity_id: EntityID | None = Field(
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
        deprecated=True,
        title="Base name",
        description="The base name of the user - first, middle, and last name without any prefixes or suffixes. Organized as a list of strings with each part.",
    )

    @computed_field(return_type=list[str])
    def names(self) -> list[str]:
        first = (self.first_name or "").strip() if self.first_name else ""
        last = (self.last_name or "").strip() if self.last_name else ""
        middle = " ".join(self.middle_names) if self.middle_names else ""
        names: list[str] = []
        if first or last:
            names.append(f"{first} {last}".strip())
        if first or middle or last:
            names.append(f"{first} {middle} {last}".strip())
        if self.prefixes:
            for pfx in self.prefixes:
                if last:
                    names.append(f"{pfx} {last}".strip())
                if first and last:
                    names.append(f"{pfx} {first} {last}".strip())
                if self.suffixes and first and last:
                    for sfx in self.suffixes:
                        names.append(f"{pfx} {first} {last}, {sfx}".strip())
                        names.append(f"{pfx} {last}, {sfx}".strip())
                        names.append(f"{first} {last}, {sfx}".strip())
        # Fallback to preferred_name if nothing else
        if not names and self.preferred_name:
            names.append(self.preferred_name)
        return [n for n in names if n]

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
        linked_entity_id: str | None = None,
        linked_entity: Entity | None = None,
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
            linked_entity_id (str): The ID of the user-linked entity
            linked_entity (Entity): The user-linked entity object

        User-linked Entity:

            If specifying a new user entity, provide either the linked_entity_id or the linked_entity object itself.
            Warning: the new linked ID or Entity object should be validated prior to calling this function.
        """

        if linked_entity_id and linked_entity:
            logger.warning(
                "Both linked_entity_id and linked_entity provided - prioritizing linked_entity"
            )
        elif linked_entity_id and not linked_entity:
            validate_id_simple(linked_entity_id)
        elif linked_entity and not linked_entity_id:
            validate_id_simple(linked_entity.id)
            linked_entity_id = linked_entity.id
        else:
            raise ValueError("Must provide either linked_entity_id or linked_entity")

        # Compose preferred name from the provided information if not provided
        if not preferred_name:
            # Make sure there's enough data to work with
            if not first_name and not last_name and not nickname and not middle_names:
                raise ValueError("Not enough data to compose a preferred name")

            # First, try prefix + first name
            if prefixes and first_name:
                preferred_name = f"{prefixes[0]} {first_name}"

            # Then, try just first name
            elif first_name:
                preferred_name = first_name

            # Then, try just last name
            elif last_name:
                preferred_name = last_name

            # Then, try nickname
            elif nickname:
                preferred_name = nickname

            # Then, try middle names
            elif middle_names:
                preferred_name = " ".join(middle_names)
            else:
                raise ValueError("Not enough data to compose a preferred name for the user")

        base_name = None  # deprecated

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
            base_name=base_name,
            linked_entity_id=linked_entity_id,
        )

    @classmethod
    def from_default(cls) -> "UserIdentifier":
        """Create and return a default UserIdentifier."""
        return cls(
            first_name="user",
            preferred_name="user",
            pronouns="they/them",
        )

    @classmethod
    def from_dict(cls, data: dict) -> "UserIdentifier":
        """Create a UserIdentifier from a dictionary of values."""
        user_info: dict[str, Any] = {}

        # Filter for accepted values
        for k in [
            "preferred_name",
            "first_name",
            "last_name",
            "middle_names",
            "pronouns",
            "nickname",
            "prefixes",
            "suffixes",
            "emails",
            "linked_entity_id",
        ]:
            if k in data and data[k]:
                user_info[k] = data[k]

        # Quick validation of list types
        if user_info.get("middle_names"):
            user_info["middle_names"] = [str(m) for m in user_info.get("middle_names", [])]
        if user_info.get("prefixes"):
            user_info["prefixes"] = [str(p) for p in user_info.get("prefixes", [])]
        if user_info.get("suffixes"):
            user_info["suffixes"] = [str(s) for s in user_info.get("suffixes", [])]
        if user_info.get("emails"):
            user_info["emails"] = [str(e) for e in user_info.get("emails", [])]

        # Quick ID validation if provided - should be fully validated first by the manager
        if user_info.get("linked_entity_id"):
            validate_id_simple(user_info["linked_entity_id"])

        # Create the user info object
        new_user_info = cls.from_values(**user_info)

        return new_user_info


class GraphMeta(BaseModel):
    schema_version: int = Field(
        default=IQ_MCP_SCHEMA_VERSION, description="Schema/memory record version"
    )
    app_version: str = Field(default=IQ_MCP_VERSION, description="Application version")
    graph_id: EntityID = Field(
        default_factory=lambda: str(uuid4())[:8], description="Graph identifier"
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
    meta: GraphMeta = Field(
        ...,
        title="Graph metadata",
        description="Optional metadata about the knowledge graph (schema versioning, ids, etc.)",
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
    def from_components(
        cls,
        user_info: UserIdentifier,
        entities: list[Entity],
        relations: list[Relation],
        meta: GraphMeta,
    ) -> "KnowledgeGraph":
        """Initialize the knowledge graph by passing in the user info object, entities lists, and relations lists."""
        return cls(
            user_info=user_info,
            entities=entities,
            relations=relations,
            meta=meta,
        )

    @classmethod
    def from_default(cls) -> "KnowledgeGraph":
        """Initialize the knowledge graph with default values."""
        from mcp_knowledge_graph.utils.seed_graph import build_initial_graph

        return build_initial_graph()

    def to_dict_list(self) -> list[dict]:
        """Return the knowledge graph as a list of dictionaries suitable for writing to a JSONL file."""
        result = [self.user_info.model_dump(exclude_none=True)]
        result.extend([e.model_dump(exclude_none=True) for e in (self.entities or [])])
        result.extend([r.model_dump(exclude_none=True) for r in (self.relations or [])])
        return result

    def validate(self) -> None:
        """
        Run a comprehensive validation of the knowledge graph.
        This includes:
        - Validating the user info: Checks for a preferred name and that the linked entity exists in the graph
        - Validating entities: Checks for unique and valid IDs and the absence of duplicates
        - Validating observations: Checks for valid timestamps and durability, and the absence of duplicates (per entity)
        - Validating relations: Checks for valid from and to IDs and the absence of duplicates
        - Validating metadata: Checks for valid schema version and app version
        """
        # Validate entities and their observations
        entity_id_map = {e.id: e for e in self.entities}
        for e in self.entities:
            ents = [en for en in self.entities if en is not e]
            ents_map = {en.id: en for en in ents}
            try:
                _ = EntityID(e.id)
            except Exception as e:
                raise KnowledgeGraphException(
                    f"Graph validation failed: Entity ID {e.id} is invalid: {e}"
                )
            if e.id in ents_map.keys():
                raise KnowledgeGraphException(
                    f"Graph validation failed: Entity ID {e.id} has a duplicate ID!"
                )
            if e in ents:
                raise KnowledgeGraphException(
                    f"Graph validation failed: Entity {e.id} is a duplicate of another entity!"
                )
            for o in e.observations:
                obs = [o for o in e.observations if o is not o]
                try:
                    _ = Observation.from_values(
                        content=o.content,
                        durability=o.durability,
                        timestamp=o.timestamp,
                    )
                except Exception as e:
                    raise KnowledgeGraphException(
                        f"Graph validation failed: Observation '{o}' is invalid: {e}"
                    )
                if o in obs:
                    raise KnowledgeGraphException(
                        f"Graph validation failed: Entity {e.id}: Observation {o} is a duplicate of another observation!"
                    )

        # Validate relations
        for r in self.relations:
            rels = [re for re in self.relations if re is not r]
            try:
                _ = EntityID(r.from_id)
            except Exception as e:
                raise KnowledgeGraphException(
                    f"Graph validation failed: Relation from ID {r.from_id} is invalid: {e}"
                )
            try:
                _ = EntityID(r.to_id)
            except Exception as e:
                raise KnowledgeGraphException(
                    f"Graph validation failed: Relation to ID {r.to_id} is invalid: {e}"
                )
            if r.from_id not in entity_id_map.keys():
                raise KnowledgeGraphException(
                    f"Graph validation failed: Relation from ID {r.from_id} has a duplicate ID!"
                )
            if r.to_id not in entity_id_map.keys():
                raise KnowledgeGraphException(
                    f"Graph validation failed: Relation to ID {r.to_id} has a duplicate ID!"
                )
            if r in rels:
                raise KnowledgeGraphException(
                    f"Graph validation failed: Relation {r.from_id} -> {r.to_id} is a duplicate of another relation!"
                )

        # Validate user info
        if not self.user_info.preferred_name:
            raise KnowledgeGraphException(
                "Graph validation failed: User info must have a preferred name!"
            )
        if not self.user_info.linked_entity_id:
            raise KnowledgeGraphException(
                "Graph validation failed: User info must have a linked entity ID!"
            )
        if self.user_info.linked_entity_id not in entity_id_map.keys():
            raise KnowledgeGraphException(
                f"Graph validation failed: User info linked entity ID {self.user_info.linked_entity_id} is invalid!"
            )

        # Validate metadata
        if not self.meta.schema_version:
            raise KnowledgeGraphException(
                "Graph validation failed: Metadata must have a schema version!"
            )
        if not self.meta.app_version:
            raise KnowledgeGraphException(
                "Graph validation failed: Metadata must have an app version!"
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
    entity_id: EntityID | None = Field(
        default=None,
        title="Entity ID",
        description="The ID of the entity to add observations to",
        validation_alias=AliasChoices("entity_id", "id"),
    )
    observations: list[Observation] = Field(
        ...,
        title="Observations",
        description="Observations to add - objects with durability metadata",
    )


class CreateEntityRequest(BaseModel):
    """
    Request model used to create an entity.

    Properties:
        name (str): The name of the new entity to create.
        entity_type (str): The type of the entity. Arbitrary, but should be a noun.
        observations (list[Observation]): The observations of the entity. Optional, but recommended.
        aliases (list[str]): Any alternative names for the entity
        icon (str): The icon of the entity. Must be a single valid emoji. Optional, but recommended.

    If valid, the entity will automatically be assigned an ID and observations will be given timestamps.
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

    @field_validator("name", "entity_type", mode="before")
    @classmethod
    def _strip_and_require(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("must not be empty")
        return v


class CreateEntityResult(BaseModel):
    """Model for the result of creating an entity."""

    entity: Entity | dict[str, Any] = Field(
        ...,
        title="Entity",
        description="The entity that was successfully created, or the unsuccessful entity with errors",
    )
    errors: list[str] | None = Field(
        default=None,
        title="Errors",
        description="Messages, warnings, or errors to return to the LLM or user, if applicable",
    )


class UpdateEntityRequest(BaseModel):
    """Request model used to update an entity in the knowledge graph."""

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
        validate_by_alias=True,
    )
    identifiers: list[str] | list[EntityID] = (
        Field(
            default=None,
            description="Entity names, aliases, or IDs to identify the target entities to update",
        ),
    )
    new_name: str = (Field(default=None, description="New canonical name for the updated entity"),)
    new_type: str | None = (Field(default=None, description="New type for the updated entity"),)
    new_aliases: str | list[str] | None = (
        Field(
            default=None,
            description="Aliases to set for the merged entity (merged by default; set merge_aliases=false to replace)",
        ),
    )
    new_icon: str | None = (
        Field(
            default=None,
            description="Emoji icon to set for the merged entity; use empty string to clear",
        ),
    )
    merge_aliases: bool = (
        Field(
            default=True,
            description="When true, merge provided aliases for the merged entity; when false, replace alias list",
        ),
    )


class UpdateEntityResult(BaseModel):
    """Data model for the result of updating an entity."""

    entity: Entity | None = Field(
        ...,
        title="Entity",
        description="The resulting merged entity, or None if the update failed",
    )
    errors: list[str] | None = Field(
        default=None,
        title="Errors",
        description="Messages, warnings, or errors to return to the LLM or user, if applicable",
    )
    success: bool = Field(
        ...,
        title="Success",
        description="Whether the entity was updated successfully",
    )


class CreateRelationRequest(BaseModel):
    """Request model used to create a relation. If a name is provided, it will be used to match the entity to an ID."""

    model_config = ConfigDict(
        populate_by_name=True,
        validate_by_name=True,
    )

    from_entity_id: EntityID | None = Field(
        title="Originating entity ID",
        description="The ID of the entity to create a relation from",
        validation_alias=AliasChoices("from_entity_id", "from_id", "fromId"),
    )
    to_entity_id: EntityID | None = Field(
        title="Destination entity ID",
        description="The ID of the entity to create a relation to",
        validation_alias=AliasChoices("to_entity_id", "to_id", "toId"),
    )
    from_entity_name: str | None = Field(
        default=None,
        title="Originating entity name",
        description="The name of the entity to create a relation from",
        validation_alias=AliasChoices("from_entity_name", "from_name", "from"),
    )
    to_entity_name: str | None = Field(
        default=None,
        title="Destination entity name",
        description="The name of the entity to create a relation to",
        validation_alias=AliasChoices("to_entity_name", "to_name", "to"),
    )
    relation: str = Field(
        ...,
        title="Relation content",
        description="Description of the relation. Should be in active voice and concise. Example: 'is the father of'",
    )

    # ID validation handled by constrained types above

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


class AddObservationResult(BaseModel):
    """Result of adding observations to an entity."""

    entity: Entity | dict[str, Any] = Field(
        ...,
        title="Entity",
        description="The entity that was updated",
    )
    added_observations: list[Observation] | None = Field(
        default=None,
        title="Added observations",
        description="The observations that were actually added (excluding duplicates and errors)",
    )
    errors: list[str] | None = Field(
        default=None,
        title="Errors",
        description="Messages, warnings, or errors to return to the LLM or user, if applicable",
    )


class DeleteObservationRequest(BaseModel):
    """Request model for deleting observations from an entity."""

    entity_name: str = Field(
        ...,
        title="Entity name",
        description="The name of the entity containing the observations",
    )
    entity_id: EntityID | None = Field(
        default=None,
        title="Entity ID",
        description="The ID of the entity containing the observations",
        validation_alias=AliasChoices("entity_id", "id"),
    )
    observations: list[str] = Field(
        ...,
        title="Observations",
        description="Array of observation contents to delete",
    )

    def __repr__(self):
        return f"DeleteObservationRequest(entity_name={self.entity_name}, observations={self.observations})"


# DEPRECATED CLASSES
class DeleteEntryRequest(BaseModel):
    """Request model used to delete data from the knowledge graph.

    Properties:
        - 'entry_type' (str): must be one of: 'observation', 'entity', or 'relation'
        - 'data' (list[AddObservationRequest] | list[str] | list[Relation]): must be a list of the appropriate object for each entry_type:
            - entry_type = 'entity': list of entity IDs
            - entry_type = 'observation': [{entity_id, [observation content]}]
            - entry_type = 'relation': [{from_entity, to_entity, relation}]
    """

    entry_type: Literal["observation", "entity", "relation"] = Field(
        description="Type of entry to create: 'observation', 'entity', or 'relation'"
    )
    data: list[DeleteObservationRequest] | list[EntityID] | list[Relation] | None = Field(
        description="""A list of the appropriate object for the given entry_type.

        - entry_type = 'entity': list of entity IDs
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


# class CreateEntityResult(BaseModel):
#     """DEPRECATED: Result of creating an entity."""

#     entities: list[Entity] = Field(
#         ...,
#         title="Entities",
#         description="The entities that were successfully created (excludes existing names)",
#     )


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


# Structured JSONL record for storage IO
class MemoryRecord(BaseModel):
    type: Literal["meta", "user_info", "entity", "relation"]
    data: Any
