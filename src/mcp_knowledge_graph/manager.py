"""
Knowledge Graph Manager with temporal observation support.

This module contains the core business logic for managing the knowledge graph,
including CRUD operations, temporal observation handling, and smart cleanup.
"""

import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Union, Dict, Set
from pathlib import Path

from .models import (
    Entity,
    Relation,
    KnowledgeGraph,
    TimestampedObservation,
    ObservationInput,
    AddObservationRequest,
    AddObservationResult,
    DeleteObservationRequest,
    CleanupResult,
    DurabilityGroupedObservations,
    DurabilityType,
)


logger = logging.getLogger("iq-mcp")
logger.setLevel(logging.DEBUG)


class KnowledgeGraphManager:
    """
    Core manager for knowledge graph operations with temporal features.

    This class handles all CRUD operations on the knowledge graph while maintaining
    backward compatibility with string observations and providing enhanced temporal
    features for smart memory management.
    """

    def __init__(self, memory_file_path: str):
        """
        Initialize the knowledge graph manager.

        Args:
            memory_file_path: Path to the JSONL file for persistent storage
        """
        self.memory_file_path = Path(memory_file_path)
        # Ensure the directory exists
        self.memory_file_path.parent.mkdir(parents=True, exist_ok=True)

    def _create_timestamped_observation(
        self, input_data: str | ObservationInput
    ) -> TimestampedObservation:
        """
        Create a timestamped observation from input.

        Converts string observations (old format) or ObservationInput objects
        to the new TimestampedObservation format with current timestamp.

        Args:
            input_data: Either a string or ObservationInput object

        Returns:
            TimestampedObservation with current timestamp
        """
        if isinstance(input_data, str):
            # Convert old string format with default durability
            return TimestampedObservation.create_now(
                content=input_data, durability=DurabilityType.LONG_TERM
            )

        # Handle ObservationInput object
        return TimestampedObservation.create_now(
            content=input_data.content, durability=input_data.durability or DurabilityType.LONG_TERM
        )

    def _normalize_observation(
        self, obs: Union[str, TimestampedObservation]
    ) -> TimestampedObservation:
        """
        Normalize observations to TimestampedObservation format.

        This ensures backward compatibility by converting old string observations
        to the new temporal format when loading from storage.

        Args:
            obs: Either a string or TimestampedObservation

        Returns:
            TimestampedObservation with appropriate metadata
        """
        if isinstance(obs, str):
            return self._create_timestamped_observation(obs)
        return obs

    def _is_observation_outdated(self, obs: TimestampedObservation) -> bool:
        """
        Check if an observation is likely outdated based on durability and age.

        Args:
            obs: The observation to check

        Returns:
            True if the observation should be considered outdated
        """
        try:
            now = datetime.now()
            obs_date = datetime.fromisoformat(obs.timestamp.replace("Z", "+00:00"))
            days_old = (now - obs_date).days
            months_old = days_old / 30.0

            if obs.durability == DurabilityType.PERMANENT:
                return False  # Never outdated
            elif obs.durability == DurabilityType.LONG_TERM:
                return months_old > 24  # 2+ years old
            elif obs.durability == DurabilityType.SHORT_TERM:
                return months_old > 6  # 6+ months old
            elif obs.durability == DurabilityType.TEMPORARY:
                return months_old > 1  # 1+ month old
            else:
                return False
        except (ValueError, AttributeError):
            # If timestamp parsing fails, assume not outdated
            return False

    async def _load_graph(self) -> KnowledgeGraph:
        """
        Load the knowledge graph from JSONL storage.

        Returns:
            KnowledgeGraph loaded from file, or empty graph if file doesn't exist
        """
        if not self.memory_file_path.exists():
            return KnowledgeGraph()

        try:
            entities = []
            relations = []

            with open(self.memory_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        item = json.loads(line)
                        if item.get("type") == "entity":
                            # Remove the type field and create Entity
                            entity_data = {k: v for k, v in item.items() if k != "type"}
                            entity = Entity(**entity_data)
                            # Normalize observations when loading
                            entity.observations = [
                                self._normalize_observation(obs) for obs in entity.observations
                            ]
                            entities.append(entity)
                        elif item.get("type") == "relation":
                            # Remove the type field and create Relation
                            relation_data = {k: v for k, v in item.items() if k != "type"}
                            relations.append(Relation(**relation_data))
                    except (json.JSONDecodeError, ValueError) as e:
                        # Skip invalid lines but continue processing
                        print(f"Warning: Skipping invalid line in {self.memory_file_path}: {e}")
                        continue

            return KnowledgeGraph(entities=entities, relations=relations)

        except Exception as e:
            print(f"Error loading graph: {e}")
            return KnowledgeGraph()

    async def _save_graph(self, graph: KnowledgeGraph) -> None:
        """
        Save the knowledge graph to JSONL storage.

        Args:
            graph: The knowledge graph to save
        """
        try:
            lines = []

            # Save entities
            for entity in graph.entities:
                entity_dict = entity.dict(by_alias=True)
                entity_dict["type"] = "entity"
                lines.append(json.dumps(entity_dict, separators=(",", ":")))

            # Save relations
            for relation in graph.relations:
                relation_dict = relation.dict(by_alias=True)
                relation_dict["type"] = "relation"
                lines.append(json.dumps(relation_dict, separators=(",", ":")))

            with open(self.memory_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

        except Exception as e:
            raise RuntimeError(f"Failed to save graph: {e}")

    async def create_entities(self, entities: List[Entity]) -> List[Entity]:
        """
        Create multiple new entities in the knowledge graph.

        Args:
            entities: List of entities to create

        Returns:
            List of entities that were actually created (excludes existing names)
        """
        graph = await self._load_graph()
        existing_names = {entity.name for entity in graph.entities}

        new_entities = [entity for entity in entities if entity.name not in existing_names]

        graph.entities.extend(new_entities)
        await self._save_graph(graph)
        return new_entities

    async def create_relations(self, relations: List[Relation]) -> List[Relation]:
        """
        Create multiple new relations between entities.

        Args:
            relations: List of relations to create

        Returns:
            List of relations that were actually created (excludes duplicates)
        """
        graph = await self._load_graph()

        # Create set of existing relations for duplicate checking
        existing_relations = {
            (r.from_entity, r.to_entity, r.relation_type) for r in graph.relations
        }

        new_relations = [
            relation
            for relation in relations
            if (relation.from_entity, relation.to_entity, relation.relation_type)
            not in existing_relations
        ]

        graph.relations.extend(new_relations)
        await self._save_graph(graph)
        return new_relations

    async def add_observations(
        self, requests: List[AddObservationRequest]
    ) -> List[AddObservationResult]:
        """
        Add new observations to existing entities with temporal metadata.

        Args:
            requests: List of observation addition requests

        Returns:
            List of results showing what was actually added

        Raises:
            ValueError: If an entity is not found
        """
        graph = await self._load_graph()
        results = []

        for request in requests:
            # Find the entity
            entity = next((e for e in graph.entities if e.name == request.entity_name), None)
            if entity is None:
                raise ValueError(f"Entity with name {request.entity_name} not found")

            # Convert all input contents to TimestampedObservation format
            new_timestamped_obs = [
                self._create_timestamped_observation(content) for content in request.contents
            ]

            # Get existing observation contents for duplicate checking
            existing_contents = {
                obs.content if isinstance(obs, TimestampedObservation) else obs
                for obs in entity.observations
            }

            # Filter out duplicates
            unique_new_obs = [
                obs for obs in new_timestamped_obs if obs.content not in existing_contents
            ]

            # Add new observations
            entity.observations.extend(unique_new_obs)

            results.append(
                AddObservationResult(
                    entity_name=request.entity_name, added_observations=unique_new_obs
                )
            )

        await self._save_graph(graph)
        return results

    async def cleanup_outdated_observations(self) -> CleanupResult:
        """
        Remove observations that are likely outdated based on durability and age.

        Returns:
            CleanupResult with details of what was removed
        """
        graph = await self._load_graph()
        total_removed = 0
        removed_details = []

        for entity in graph.entities:
            original_count = len(entity.observations)

            # Normalize all observations first
            normalized_obs = [self._normalize_observation(obs) for obs in entity.observations]

            # Filter out outdated observations
            kept_observations = []
            for obs in normalized_obs:
                if self._is_observation_outdated(obs):
                    try:
                        obs_date = datetime.fromisoformat(obs.timestamp.replace("Z", "+00:00"))
                        age_days = (datetime.now() - obs_date).days
                        removed_details.append(
                            {
                                "entityName": entity.name,
                                "content": obs.content,
                                "age": f"{age_days} days old",
                            }
                        )
                    except ValueError:
                        removed_details.append(
                            {
                                "entityName": entity.name,
                                "content": obs.content,
                                "age": "unknown age",
                            }
                        )
                else:
                    kept_observations.append(obs)

            entity.observations = kept_observations
            total_removed += original_count - len(kept_observations)

        if total_removed > 0:
            await self._save_graph(graph)

        return CleanupResult(
            entities_processed=len(graph.entities),
            observations_removed=total_removed,
            removed_observations=removed_details,
        )

    async def get_observations_by_durability(
        self, entity_name: str
    ) -> DurabilityGroupedObservations:
        """
        Get observations for an entity grouped by durability type.

        Args:
            entity_name: The name of the entity to get observations for

        Returns:
            Observations grouped by durability type

        Raises:
            ValueError: If the entity is not found
        """
        graph = await self._load_graph()
        entity = next((e for e in graph.entities if e.name == entity_name), None)

        if entity is None:
            raise ValueError(f"Entity {entity_name} not found")

        # Normalize all observations
        normalized_obs = [self._normalize_observation(obs) for obs in entity.observations]

        # Group by durability
        grouped = DurabilityGroupedObservations()
        for obs in normalized_obs:
            if obs.durability == DurabilityType.PERMANENT:
                grouped.permanent.append(obs)
            elif obs.durability == DurabilityType.LONG_TERM:
                grouped.long_term.append(obs)
            elif obs.durability == DurabilityType.SHORT_TERM:
                grouped.short_term.append(obs)
            elif obs.durability == DurabilityType.TEMPORARY:
                grouped.temporary.append(obs)

        return grouped

    async def delete_entities(self, entity_names: List[str]) -> None:
        """
        Delete multiple entities and their associated relations.

        Args:
            entity_names: List of entity names to delete
        """
        graph = await self._load_graph()
        entity_names_set = set(entity_names)

        # Remove entities
        graph.entities = [e for e in graph.entities if e.name not in entity_names_set]

        # Remove relations involving deleted entities
        graph.relations = [
            r
            for r in graph.relations
            if r.from_entity not in entity_names_set and r.to_entity not in entity_names_set
        ]

        await self._save_graph(graph)

    async def delete_observations(self, deletions: List[DeleteObservationRequest]) -> None:
        """
        Delete specific observations from entities.

        Args:
            deletions: List of observation deletion requests
        """
        graph = await self._load_graph()

        for deletion in deletions:
            entity = next((e for e in graph.entities if e.name == deletion.entity_name), None)
            if entity:
                # Create set of observations to delete
                to_delete = set(deletion.observations)

                # Filter out observations that match the deletion content
                entity.observations = [
                    obs
                    for obs in entity.observations
                    if (obs.content if isinstance(obs, TimestampedObservation) else obs)
                    not in to_delete
                ]

        await self._save_graph(graph)

    async def delete_relations(self, relations: List[Relation]) -> None:
        """
        Delete multiple relations from the knowledge graph.

        Args:
            relations: List of relations to delete
        """
        graph = await self._load_graph()

        # Create set of relations to delete for efficient lookup
        to_delete = {(r.from_entity, r.to_entity, r.relation_type) for r in relations}

        # Filter out matching relations
        graph.relations = [
            r
            for r in graph.relations
            if (r.from_entity, r.to_entity, r.relation_type) not in to_delete
        ]

        await self._save_graph(graph)

    async def read_graph(self) -> KnowledgeGraph:
        """
        Read the entire knowledge graph.

        Returns:
            The complete knowledge graph
        """
        return await self._load_graph()

    async def search_nodes(self, query: str) -> KnowledgeGraph:
        """
        Search for nodes in the knowledge graph based on a query.

        Args:
            query: Search query to match against names, types, and observation content

        Returns:
            Filtered knowledge graph containing only matching entities and their relations
        """
        graph = await self._load_graph()
        query_lower = query.lower()

        # Filter entities that match the query
        filtered_entities = []
        for entity in graph.entities:
            # Check entity name and type
            if query_lower in entity.name.lower() or query_lower in entity.entity_type.lower():
                filtered_entities.append(entity)
                continue

            # Check observations
            for obs in entity.observations:
                content = obs.content if isinstance(obs, TimestampedObservation) else obs
                if query_lower in content.lower():
                    filtered_entities.append(entity)
                    break

        # Get names of filtered entities for relation filtering
        filtered_entity_names = {entity.name for entity in filtered_entities}

        # Filter relations between filtered entities
        filtered_relations = [
            r
            for r in graph.relations
            if r.from_entity in filtered_entity_names and r.to_entity in filtered_entity_names
        ]

        return KnowledgeGraph(entities=filtered_entities, relations=filtered_relations)

    async def open_nodes(self, names: List[str]) -> KnowledgeGraph:
        """
        Open specific nodes in the knowledge graph by their names.

        Args:
            names: List of entity names to retrieve

        Returns:
            Knowledge graph containing only the specified entities and their relations
        """
        graph = await self._load_graph()
        names_set = set(names)

        # Filter entities by name
        filtered_entities = [e for e in graph.entities if e.name in names_set]

        # Filter relations between the specified entities
        filtered_relations = [
            r for r in graph.relations if r.from_entity in names_set and r.to_entity in names_set
        ]

        return KnowledgeGraph(entities=filtered_entities, relations=filtered_relations)
