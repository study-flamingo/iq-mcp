"""
Data models for the temporal knowledge graph memory system.

This module defines all the data structures used throughout the knowledge graph,
including entities, relations, and temporal observations with durability metadata.
"""

from datetime import datetime
from typing import List, Union, Literal, Optional
from pydantic import BaseModel, Field
from enum import Enum


class DurabilityType(str, Enum):
    """Enumeration of observation durability categories."""
    
    PERMANENT = "permanent"      # Never expires (e.g., "Born in 1990", "Has a degree in Physics")
    LONG_TERM = "long-term"      # Relevant for 2+ years (e.g., "Works at Acme Corp", "Lives in New York")
    SHORT_TERM = "short-term"    # Relevant for ~6 months (e.g., "Working on Project X", "Training for a marathon")
    TEMPORARY = "temporary"      # Relevant for ~1 month (e.g., "Currently learning TypeScript", "Traveling to Dominica")


class TimestampedObservation(BaseModel):
    """
    Enhanced observation structure with temporal metadata.
    
    Observations now include timestamps and durability categories to distinguish
    between permanent facts and temporary states.
    """
    
    content: str = Field(..., description="The observation content")
    timestamp: str = Field(..., description="ISO date string when the observation was created")
    durability: DurabilityType = Field(..., description="How long this observation is expected to remain relevant")
    
    @classmethod
    def create_now(cls, content: str, durability: DurabilityType = DurabilityType.LONG_TERM) -> "TimestampedObservation":
        """Create a new timestamped observation with current timestamp."""
        return cls(
            content=content,
            timestamp=datetime.now().isoformat(),
            durability=durability
        )


class ObservationInput(BaseModel):
    """
    Helper model for creating observations with optional durability.
    
    This makes durability optional when creating new observations,
    defaulting to 'long-term' for backward compatibility.
    """
    
    content: str = Field(..., description="The observation content")
    durability: Optional[DurabilityType] = Field(default=DurabilityType.LONG_TERM, description="How long this observation is expected to remain relevant")


class Entity(BaseModel):
    """
    Primary nodes in the knowledge graph.
    
    Each entity has a unique name, type classification, and list of observations
    that support both old string format and new temporal format for backward compatibility.
    """
    
    name: str = Field(..., description="Unique identifier for the entity")
    entity_type: str = Field(..., description="Type classification (e.g., 'person', 'organization', 'event')", alias="entityType")
    observations: List[Union[str, TimestampedObservation]] = Field(default_factory=list, description="Associated observations in string or temporal format")
    
    class Config:
        populate_by_name = True


class Relation(BaseModel):
    """
    Directed connections between entities.
    
    Relations are stored in active voice and describe how entities
    interact or relate to each other.
    """
    
    from_entity: str = Field(..., description="Source entity name", alias="from")
    to_entity: str = Field(..., description="Target entity name", alias="to") 
    relation_type: str = Field(..., description="Relationship type in active voice", alias="relationType")
    
    class Config:
        populate_by_name = True


class KnowledgeGraph(BaseModel):
    """
    Complete knowledge graph containing entities and their relations.
    
    This is the top-level container for the entire memory system,
    supporting both entities and the relations between them.
    """
    
    entities: List[Entity] = Field(default_factory=list, description="All entities in the knowledge graph")
    relations: List[Relation] = Field(default_factory=list, description="All relations between entities")


class CleanupResult(BaseModel):
    """Result of cleaning up outdated observations."""
    
    entities_processed: int = Field(..., description="Number of entities that were processed")
    observations_removed: int = Field(..., description="Total number of observations removed")
    removed_observations: List[dict] = Field(default_factory=list, description="Details of removed observations")


class DurabilityGroupedObservations(BaseModel):
    """Observations grouped by their durability type."""
    
    permanent: List[TimestampedObservation] = Field(default_factory=list)
    long_term: List[TimestampedObservation] = Field(default_factory=list)
    short_term: List[TimestampedObservation] = Field(default_factory=list)
    temporary: List[TimestampedObservation] = Field(default_factory=list)


class AddObservationRequest(BaseModel):
    """Request model for adding observations to an entity."""
    
    entity_name: str = Field(..., description="The name of the entity to add observations to")
    contents: List[Union[str, ObservationInput]] = Field(..., description="Observations to add - can be simple strings or objects with durability metadata")


class AddObservationResult(BaseModel):
    """Result of adding observations to an entity."""
    
    entity_name: str = Field(..., description="The entity name that was updated")
    added_observations: List[TimestampedObservation] = Field(..., description="The observations that were actually added (excluding duplicates)")


class DeleteObservationRequest(BaseModel):
    """Request model for deleting observations from an entity."""
    
    entity_name: str = Field(..., description="The name of the entity containing the observations")
    observations: List[str] = Field(..., description="Array of observation contents to delete")