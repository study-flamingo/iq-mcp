"""
Knowledge Graph Manager with temporal observation support.

This module contains the core business logic for managing the knowledge graph,
including CRUD operations, temporal observation handling, and smart cleanup.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from pathlib import Path
from uuid import uuid4
from .settings import Settings as settings, Logger as logger

from .models import (
    Entity,
    Relation,
    KnowledgeGraph,
    Observation,
    ObservationRequest,
    AddObservationResult,
    DeleteObservationRequest,
    CleanupResult,
    DurabilityGroupedObservations,
    DurabilityType,
    CreateEntityResult,
    CreateRelationResult,
    UserIdentifier,
    KnowledgeGraphException,
)


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

    @classmethod
    def from_settings(cls) -> "KnowledgeGraphManager":
        """
        Initialize the knowledge graph manager via the settings object.
        """
        # Uses the already-initialized settings object
        return cls(settings.memory_file_path)

    # ---------- Alias helpers ----------
    def _get_entity_by_name_or_alias(self, graph: KnowledgeGraph, identifier: str) -> Entity | None:
        """Return the first entity whose name or aliases match the identifier (case-insensitive)."""
        ident_lower = (identifier or "").strip().lower()
        if not ident_lower:
            return None
        for entity in graph.entities:
            if entity.name.lower() == ident_lower:
                return entity
            # Ensure aliases exists and compare case-insensitively
            try:
                for alias in entity.aliases:
                    if isinstance(alias, str) and alias.strip().lower() == ident_lower:
                        return entity
            except Exception:
                # In case legacy data has non-list or invalid aliases field
                pass
        return None

    def _get_entity_by_id(self, id: str, graph: KnowledgeGraph) -> Entity | None:
        """
        Return the entity whose ID matches the provided ID.
        If no entity is found, returns None.

        Intended for use during loading and validation of the graph.
        """
        if not id:
            return None
        for e in graph.entities:
            if e.id == id:
                return e
        return None

    def _canonicalize_entity_name(self, graph: KnowledgeGraph, identifier: str) -> str:
        """Return canonical entity name if identifier matches a name or alias; otherwise return identifier unchanged."""
        entity = self._get_entity_by_name_or_alias(graph, identifier)
        return entity.name if entity else identifier

    def _format_observation_age(self, timestamp: str | datetime | None) -> str:
        """Return a human-friendly age string for a timestamp; fallback to 'unknown age'."""
        try:
            if not timestamp:
                return "unknown age"

            if isinstance(timestamp, str):
                obs_date = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                obs_date = timestamp

            # Normalize to timezone-aware UTC
            if obs_date.tzinfo is None:
                obs_date = obs_date.replace(tzinfo=timezone.utc)
            else:
                obs_date = obs_date.astimezone(timezone.utc)

            now = datetime.now(timezone.utc)
            age_days = (now - obs_date).days
            return f"{age_days} days old"
        except Exception:
            return "unknown age"

    def _group_by_durability(
        self, observations: list[Observation]
    ) -> DurabilityGroupedObservations:
        """Group timestamped observations by durability type."""
        grouped = DurabilityGroupedObservations()
        for obs in observations:
            if obs.durability == DurabilityType.PERMANENT:
                grouped.permanent.append(obs)
            elif obs.durability == DurabilityType.LONG_TERM:
                grouped.long_term.append(obs)
            elif obs.durability == DurabilityType.SHORT_TERM:
                grouped.short_term.append(obs)
            elif obs.durability == DurabilityType.TEMPORARY:
                grouped.temporary.append(obs)
        return grouped

    def _dedupe_relations_in_place(self, relations: list[Relation]) -> list[Relation]:
        """Deduplicate relations by (from, to, type), keeping last occurrence order."""
        unique: dict[tuple[str, str, str], Relation] = {}
        for rel in relations:
            key = (rel.from_entity, rel.to_entity, rel.relation)
            unique[key] = rel
        return list(unique.values())

    def _is_observation_outdated(self, obs: Observation) -> bool:
        """
        Check if an observation is likely outdated based on durability and age.

        Args:
            obs: The observation to check

        Returns:
            True if the observation should be considered outdated
        """
        try:
            now = datetime.now(timezone.utc)

            # If the observation has no timestamp, add one
            if not obs.timestamp:
                # Normalize missing timestamp to an ISO UTC string
                obs.timestamp = now.isoformat().replace("+00:00", "Z")
                # This observation didn't have a timestamp, but now it does, so assume it's not outdated
                return False

            obs_date_any = obs.timestamp
            if isinstance(obs_date_any, str):
                obs_date = datetime.fromisoformat(obs_date_any.replace("Z", "+00:00"))
            else:
                obs_date = obs_date_any

            # Ensure timezone-aware UTC for safe arithmetic
            if obs_date.tzinfo is None:
                obs_date = obs_date.replace(tzinfo=timezone.utc)
            else:
                obs_date = obs_date.astimezone(timezone.utc)

            days_old = (now - obs_date).days
            months_old = days_old / 30.0

            if obs.durability == DurabilityType.PERMANENT:
                return False  # Never outdated
            elif obs.durability == DurabilityType.LONG_TERM:
                return months_old > 12  # 1+ years old
            elif obs.durability == DurabilityType.SHORT_TERM:
                return months_old > 3  # 3+ months old
            elif obs.durability == DurabilityType.TEMPORARY:
                return months_old > 1  # 1+ month old
            else:
                return False
        except (ValueError, AttributeError, TypeError):
            # If timestamp parsing fails, assume not outdated
            return False

    def _generate_new_entity_id(self) -> str:
        """Generate a new entity ID. Entity IDs are UUID4s truncated to 8 characters. Convenience
        function for future proofing against changes in ID format."""
        return str(uuid4())[:8]

    def _validate_new_entity_id(self, entity: Entity, graph: KnowledgeGraph) -> Entity:
        """
        Validate the ID of a new entity before it is added to the graph.

        If not set (which should not happen), generate a new one, ensure it is unique, and assign it to the entity.
        If set, check if it is unique and return the entity.

        Args:
            entity: The entity to validate.
            graph: The graph to use to get the entities list. Loads the default graph from disk if not provided.
            entities_list: You can also provide a list of entities to use to validate the ID. Takes precedence over the graph if both are provided.

        Returns:
            The Entity with the ID set and validated against the provided graph or entities list.
        """
        try:
            if not entity.id:
                logger.error(f"Entity {entity.name} has no ID, investigate!!! Generating new ID.")
                entity.id = self._generate_new_entity_id()
            for e in graph.entities:
                if e.id == entity.id:
                    logger.warning(
                        f"Entity {entity.name} has a duplicate ID: {entity.id}. Generating new ID."
                    )
                    entity.id = self._generate_new_entity_id()

            return entity
        except Exception as e:
            raise KnowledgeGraphException(f"Error validating entity ID: {e}")

    def _validate_entity(self, entity: Entity, graph: KnowledgeGraph) -> Entity:
        """
        Validates an entity object against the knowledge graph. Intended for use during loading and
        validation of the graph.

        Most data validation is handled by pydantic. Additional validation is performed on entities to ensure
        interoperability between components of the knowledge graph. This method:

        - Ensures an entity is valid and unique (including ID strings). Compares entire Entity objects, not just ID strings.
        - If the entity appears to be the user-linked entity, verify that the user_info.linked_entity_id matches the entity ID.

        Args:
            entity: The entity to validate.
            graph: The knowledge graph to use to get the entities list.

        Returns:
            The Entity with the ID set and validated against the provided graph.
        """
        # TODO: improve pydantic utilization to simplify this method
        entities_list = graph.entities

        # Ensuure the entity actually exists in the graph, and remove for the next step
        try:
            entities_list.remove(entity)
        except Exception as e:
            raise KnowledgeGraphException(f"Entity {entity.name} must exist in graph: {e}")

        try:
            # Ensure the entity has a valid ID
            if entity.id in entities_list:
                logger.warning(f"Entity {entity.name} has a duplicate ID: {entity.id}")

            # Also make sure this isn't a copy of another with a different id
            ents = []
            for e in entities_list:
                ents.append(e.model_dump(exclude_none=True, exclude={"id"}))
            entity_no_id = entity.model_dump(exclude_none=True, exclude={"id"})
            for e in ents:
                if e == entity_no_id:
                    raise KnowledgeGraphException(f"Entity {entity.id} is a duplicate of {e.id}")

            # If this entity's name is "__user__", it should be the user-linked entity
            if entity.name == "__user__":
                if entity.id != graph.user_info.linked_entity_id:
                    logger.error(
                        f"Entity named '__user__' no longer linked to user - should have ID '{graph.user_info.linked_entity_id}', but has ID {entity.id}. Giving name 'unknown'."
                    )
                    entity.name = "unknown"

            # Return the validated entity
            return entity
        except Exception as e:
            raise KnowledgeGraphException(f"Error validating existing entity ID: {e}")

    def _verify_relation(self, relation: Relation, graph: KnowledgeGraph) -> (bool, bool):
        """
        Verify that the relation endpoints exist in the graph. Returns a tuple of booleans indicating whether the from and to entities exist.

        If the entities themselves are required, use the _get_entities_from_relation() method instead.
        """
        if not relation.from_id or not relation.to_id:
            raise KnowledgeGraphException(
                f"Relation {relation.relation} missing one or both endpoint IDs!"
            )
        bad_a = True if self._get_entity_by_id(relation.from_id, graph) else False
        bad_b = True if self._get_entity_by_id(relation.to_id, graph) else False
        return bad_a, bad_b

    def _get_entities_from_relation(
        self, relation: Relation, graph: KnowledgeGraph
    ) -> (Entity | None, Entity | None):
        """
        (Internal) Resolve the entities from a Relation object. Returns the 'from' entity and 'to'
        entity as a tuple.
        """
        # Load the graph if not provided
        if not relation.from_id or not relation.to_id:
            raise ValueError(f"Relation {relation.relation} missing one or both endpoint IDs!")
        try:
            from_entity = self._get_entity_by_id(relation.from_id, graph)
            to_entity = self._get_entity_by_id(relation.to_id, graph)

            return from_entity, to_entity
        except Exception as e:
            raise KnowledgeGraphException(f"Error getting entities from relation: {e}")

    async def _load_graph(self) -> KnowledgeGraph:
        """
        Load the knowledge graph from JSONL storage.

        Returns:
            KnowledgeGraph loaded from file, or empty graph if file doesn't exist
        """
        if not self.memory_file_path.exists():
            logger.warning(
                f"⛔ Memory file not found at {self.memory_file_path}! Returning newly initialized graph."
            )
            new_graph = KnowledgeGraph.from_default()
            return new_graph

        try:
            user_info: UserIdentifier | None = None
            entities = []
            relations = []

            with open(self.memory_file_path, "r", encoding="utf-8") as f:
                i = 0
                for line in f:
                    line = line.strip()
                    if not line:
                        logger.warning(
                            f"⚠️ Skipping empty line {i} in {self.memory_file_path}: {line}"
                        )
                        break

                    try:
                        item = json.loads(line)

                        item_type = item.get("type")

                        payload: dict | None = None
                        if item_type in ("entity", "relation", "user_info"):
                            if isinstance(item.get("data"), dict):
                                payload = item["data"]
                                if not payload:
                                    raise KnowledgeGraphException(
                                        f"Item has invalid payload: {payload}"
                                    )
                            else:
                                raise KnowledgeGraphException("Item has invalid data")

                        if item_type == "entity" and isinstance(payload, dict):
                            entity = Entity.from_dict(payload)
                            entities.append(entity)
                            logger.debug(f"Line {i}: 👤 Loaded entity: {entity}")

                        elif item_type == "relation" and isinstance(payload, dict):
                            relation = Relation.from_dict(payload)
                            relations.append(relation)
                            logger.debug(f"Line {i}: 🔗 Loaded relation: {relation}")

                        elif item_type == "user_info" and isinstance(payload, dict):
                            user_info = UserIdentifier(**payload)
                            logger.debug(f"Line {i}: 😃 Loaded user info: {user_info}")

                        else:
                            # Unrecognized line; skip with warning but continue
                            raise KnowledgeGraphException(
                                f"Missing or invalid type/payload: {item_type}"
                            )
                            continue
                    except (
                        json.JSONDecodeError,
                        ValueError,
                        TypeError,
                        KnowledgeGraphException,
                    ) as e:
                        # Skip invalid lines but continue processing
                        logger.warning(
                            f"Warning: Skipping invalid line {i} in {self.memory_file_path}: {e}"
                        )
                        continue
                    except Exception as e:
                        raise RuntimeError(f"Error loading graph: {e}")
                    i += 1

            if not user_info and not entities and not relations:
                raise KnowledgeGraphException("No valid data found in memory file!")

            # Validate the loaded data
            if not user_info:
                logger.warning(
                    "No valid user info object found in memory file! Initializing new user info object with default user info."
                )
                user_info = UserIdentifier.from_default()
            if not entities:
                raise KnowledgeGraphException("No valid entities found in memory file!")
            if not relations:
                raise KnowledgeGraphException("No valid relations found in memory file!")
            logger.info(
                f"💾 Loaded {len(entities)} entities and {len(relations)} relations from memory file"
            )
            graph = KnowledgeGraph(user_info=user_info, entities=entities, relations=relations)

            # Validate the loaded data
            # Checklist:
            # Handled by pydantic:
            #   - Ensure required user_info fields are set
            #   - Ensure required entity fields are set
            #   - Ensure required relation fields are set
            # Below:
            #   - Ensure all entities have valid, unique IDs
            #   - Ensure all relation endpoints actually exist in the graph
            #   - Validate user_info's linked entity
            try:
                try:
                    for e in graph.entities:
                        e = self._validate_entity(e, graph)
                except Exception as e:
                    raise KnowledgeGraphException(f"Bad entity: {e}")
                try:
                    for r in graph.relations:
                        a, b = self._verify_relation(r, graph)
                        err = []
                        err.append(r.from_id if a else None)
                        err.append(r.to_id if b else None)
                        if err:
                            raise ValueError(
                                f"Relation {r.relation} has invalid endpoint(s): {', '.join(err)}"
                            )
                except Exception as e:
                    raise KnowledgeGraphException(f"Bad relation: {e}")
                user_ent = self._get_entity_by_id(graph.user_info.linked_entity_id, graph)
                if not user_ent:
                    raise KnowledgeGraphException(
                        f"User-linked entity {graph.user_info.linked_entity_id} not found"
                    )
                user_ent = self._validate_entity(user_ent, graph)
                if user_ent.id != graph.user_info.linked_entity_id:
                    raise KnowledgeGraphException(
                        f"User-linked entity {graph.user_info.linked_entity_id} has invalid ID: {user_ent.id}"
                    )
            except Exception as e:
                logger.warning(f"Validation failed: {e}")

            return graph

        except Exception as e:
            raise RuntimeError(f"Error loading graph: {e}")

    async def _save_graph(self, graph: KnowledgeGraph) -> None:
        """
        Save the knowledge graph to JSONL storage.

        Args:
            graph: The knowledge graph to save

        For information on the format of the graph, see the README.md file.
        """
        # Clean up outdated observations on each save (idempotent and safe)
        try:
            r = await self.cleanup_outdated_observations()
            logger.debug(
                f"🧹 Cleaned up {r.observations_removed_count} outdated observations from {r.entities_processed_count} entities"
            )
        except Exception as e:
            # Do not block saving if cleanup fails; log and continue
            logger.warning(f"Cleanup failed prior to save: {e}")

        try:
            lines = []

            # Save user info
            try:
                if graph.user_info:
                    user_info_payload = graph.user_info.model_dump(mode="json")
                    record = {"type": "user_info", "data": user_info_payload}
                    lines.append(json.dumps(record, separators=(",", ":")))
                else:
                    # If for some reason the user info is not set, save with default info
                    user_info_payload = UserIdentifier.from_default().model_dump(mode="json")
                    record = {"type": "user_info", "data": user_info_payload}
                    lines.append(json.dumps(record, separators=(",", ":")))
            except Exception as e:
                raise RuntimeError(f"Failed to save user info: {e}")

            # Save entities
            try:
                for e in graph.entities:
                    record = {
                        "type": "entity",
                        "data": e.model_dump(mode="json", exclude_none=True),
                    }
                    lines.append(json.dumps(record, separators=(",", ":")))
            except Exception as e:
                raise RuntimeError(f"Failed to save entities: {e}")

            # Save relations
            try:
                for r in graph.relations:
                    record = {
                        "type": "relation",
                        "data": r.model_dump(
                            mode="json",
                            by_alias=True,
                            exclude_none=True,
                            include={"relation", "from_id", "to_id"},
                        ),
                    }
                    lines.append(json.dumps(record, separators=(",", ":")))
            except Exception as e:
                raise RuntimeError(f"Failed to save relations: {e}")

            try:
                with open(self.memory_file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
            except Exception as e:
                raise RuntimeError(f"Failed to write graph to {self.memory_file_path}: {e}")

        except Exception as e:
            raise RuntimeError(f"Failed to save graph: {e}")

    async def create_entities(self, entities: list[Entity]) -> CreateEntityResult:
        """
        Create multiple new entities in the knowledge graph.

        Args:
            entities: list of entities to create

        Returns:
            CreateEntityResult containing the entities that were actually created (excludes existing names)
        """
        graph = await self._load_graph()
        existing_names = {entity.name for entity in graph.entities}
        existing_aliases: set[str] = set()
        for entity in graph.entities:
            try:
                for alias in entity.aliases:
                    if isinstance(alias, str):
                        existing_aliases.add(alias)
            except Exception:
                continue

        # Only create entities whose canonical name does not collide with existing names or aliases
        new_entities = [
            entity
            for entity in entities
            if entity.name not in existing_names and entity.name not in existing_aliases
        ]

        graph.entities.extend(new_entities)
        await self._save_graph(graph)
        return new_entities

    async def create_relations(self, relations: list[Relation]) -> CreateRelationResult:
        """
        Create multiple new relations between entities.

        Args:
            relations: list of relations to create

        Returns:
            list of relations that were actually created (excludes duplicates)
        """
        graph = await self._load_graph()

        # Canonicalize endpoints to entity names if aliases provided
        canonicalized: list[Relation] = []
        for rel in relations:
            from_c = self._canonicalize_entity_name(graph, rel.from_entity)
            to_c = self._canonicalize_entity_name(graph, rel.to_entity)
            canonicalized.append(
                Relation(from_entity=from_c, to_entity=to_c, relation=rel.relation)
            )

        # Create set of existing relations for duplicate checking (with canonical names)
        existing_relations = {(r.from_entity, r.to_entity, r.relation) for r in graph.relations}

        new_relations = [
            relation
            for relation in canonicalized
            if (relation.from_entity, relation.to_entity, relation.relation)
            not in existing_relations
        ]

        graph.relations.extend(new_relations)
        await self._save_graph(graph)
        return new_relations

    async def apply_observations(
        self, requests: list[ObservationRequest]
    ) -> list[AddObservationResult]:
        """
        Add new observations to existing entities with temporal metadata.

        Args:
            requests: list of observation addition requests

        Returns:
            list of results showing what was actually added, and/or any errors that occurred

        Raises:
            ValueError: If an entity is not found
        """
        graph = await self._load_graph()
        results: list[AddObservationResult] = []

        # Track errors, while allowing the tool to continue processing other requests
        errors: list[Exception] = []
        for request in requests:
            # Find the entity by name or alias
            entity = self._get_entity_by_name_or_alias(graph, request.entity_name)
            if entity is None:
                errors.append(ValueError(f"Entity with name {request.entity_name} not found"))
                continue

            # Create observations with timestamps from the request
            observations_list: list[Observation] = []
            for o in request.observations:
                observations_list.append(Observation.add_timestamp(o.content.strip(), o.durability))

            # Get existing observation contents for duplicate checking
            existing_contents = {obs.content for obs in entity.observations}

            # Filter out duplicates
            unique_new_obs = [
                obs for obs in observations_list if obs.content not in existing_contents
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

    async def get_entities_from_relation(
        self, relation: Relation
    ) -> (Entity | None, Entity | None):
        """
        Resolve the entities from a Relation object. Returns the 'from' entity and 'to' entity as a tuple.
        """
        graph = await self._load_graph()

        from_entity = self._get_entity_by_id(graph, relation.from_id)
        to_entity = self._get_entity_by_id(graph, relation.to_id)
        return from_entity, to_entity

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

            # Filter out outdated observations
            kept_observations = []
            for obs in entity.observations:
                if self._is_observation_outdated(obs):
                    removed_details.append(
                        {
                            "entity_name": entity.name,
                            "content": obs.content,
                            "age": self._format_observation_age(obs.timestamp),
                        }
                    )
                else:
                    kept_observations.append(obs)

            entity.observations = kept_observations
            total_removed += original_count - len(kept_observations)

        if total_removed > 0:
            await self._save_graph(graph)

        return CleanupResult(
            entities_processed_count=len(graph.entities),
            observations_removed_count=total_removed,
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
        entity = self._get_entity_by_name_or_alias(graph, entity_name)

        if entity is None:
            raise ValueError(f"Entity {entity_name} not found")

        return self._group_by_durability(entity.observations)

    async def delete_entities(self, entity_names: list[str]) -> None:
        """
        Delete multiple entities and their associated relations.

        Args:
            entity_names: list of entity names to delete
        """
        if not entity_names:
            raise ValueError("No entities deleted - no data provided!")

        graph = await self._load_graph()
        # Resolve identifiers to canonical entity names
        resolved_names: set[str] = set()
        for ident in entity_names:
            entity = self._get_entity_by_name_or_alias(graph, ident)
            if entity:
                resolved_names.add(entity.name)

        if not resolved_names:
            logger.warning("No entities deleted - no valid entities provided in data")

        # Remove entities
        graph.entities = [e for e in graph.entities if e.name not in resolved_names]

        # Remove relations involving deleted entities
        graph.relations = [
            r
            for r in graph.relations
            if r.from_entity not in resolved_names and r.to_entity not in resolved_names
        ]

        await self._save_graph(graph)

    async def delete_observations(self, deletions: list[DeleteObservationRequest]) -> None:
        """
        Delete specific observations from entities.

        Args:
            deletions: list of observation deletion requests
        """
        graph = await self._load_graph()

        for deletion in deletions:
            entity = self._get_entity_by_name_or_alias(graph, deletion.entity_name)
            if entity:
                # Create set of observations to delete
                to_delete = set(deletion.observations)

                # Filter out observations that match the deletion content
                entity.observations = [
                    obs for obs in entity.observations if obs.content not in to_delete
                ]

        await self._save_graph(graph)

    async def delete_relations(self, relations: list[Relation]) -> None:
        """
        Delete multiple relations from the knowledge graph.

        Args:
            relations: list of relations to delete
        """
        graph = await self._load_graph()

        # Canonicalize relation endpoints before building deletion set
        canonical_to_delete = {
            (
                self._canonicalize_entity_name(graph, r.from_entity),
                self._canonicalize_entity_name(graph, r.to_entity),
                r.relation,
            )
            for r in relations
        }

        # Filter out matching relations
        graph.relations = [
            r
            for r in graph.relations
            if (r.from_entity, r.to_entity, r.relation) not in canonical_to_delete
        ]

        await self._save_graph(graph)

    async def read_graph(self) -> KnowledgeGraph:
        """
        Read the entire knowledge graph.

        Returns:
            The complete knowledge graph
        """
        graph = await self._load_graph()
        return graph

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
            name_match = query_lower in entity.name.lower()
            type_match = query_lower in entity.entity_type.lower()
            alias_match = False
            try:
                alias_match = any(query_lower in (a or "").lower() for a in entity.aliases)
            except Exception:
                alias_match = False

            if name_match or type_match or alias_match:
                filtered_entities.append(entity)
                continue

            # Check observations
            for obs in entity.observations:
                if query_lower in obs.content.lower():
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

        return KnowledgeGraph(
            user_info=graph.user_info,
            entities=filtered_entities,
            relations=filtered_relations,
        )

    async def open_nodes(self, names: list[str] | str) -> KnowledgeGraph:
        """
        Open specific nodes in the knowledge graph by their names.

        Args:
            names: list of entity names to retrieve

        Returns:
            Knowledge graph containing only the specified entities and their relations
        """
        graph = await self._load_graph()
        # Resolve identifiers to canonical names that exist in the graph
        names_list: list[str] = [names] if isinstance(names, str) else names
        names_set: set[str] = set()
        for ident in names_list:
            entity = self._get_entity_by_name_or_alias(graph, ident)
            if entity:
                names_set.add(entity.name)

        # Filter entities by name
        filtered_entities = [e for e in graph.entities if e.name in names_set]

        # Filter relations between the specified entities
        filtered_relations = [
            r for r in graph.relations if r.from_entity in names_set and r.to_entity in names_set
        ]

        logger.debug(f"Filtered entities: {filtered_entities}")
        logger.debug(f"Filtered relations: {filtered_relations}")
        return KnowledgeGraph(
            user_info=graph.user_info,
            entities=filtered_entities,
            relations=filtered_relations,
        )

    async def merge_entities(self, new_entity_name: str, entity_names: list[str]) -> Entity:
        """
        Merge multiple entities into a new entity with the provided name.

        - Combines observations from all entities being merged
        - Rewrites relations so any relation pointing to one of the merged
          entities now points to the new entity.
        - Removes the original entities from the graph.

        Args:
            new_entity_name: The name of the resulting merged entity
            entity_names: The list of entity names to merge

        Returns:
            The newly created merged Entity

        Raises:
            ValueError: If inputs are invalid or entities are missing/conflicting
        """
        if not new_entity_name or not isinstance(new_entity_name, str):
            raise ValueError("new_entity_name must be a non-empty string")
        if not entity_names or not isinstance(entity_names, list):
            raise ValueError("entity_names must be a non-empty list")
        if any(not isinstance(name, str) or not name for name in entity_names):
            raise ValueError("All entity_names must be non-empty strings")

        graph = await self._load_graph()

        # Canonicalize entity_names list using existing names/aliases
        canonical_merge_names: list[str] = []
        for ident in entity_names:
            entity = self._get_entity_by_name_or_alias(graph, ident)
            if not entity:
                # Collect missing for error after this loop
                canonical_merge_names.append(ident)  # keep as-is; we'll validate below
            else:
                canonical_merge_names.append(entity.name)

        # Check for name conflicts: if the new name matches an existing entity name or alias
        # that is not included in the merge set, this is a conflict.
        existing_by_name = {e.name: e for e in graph.entities}
        names_in_merge_set = set(canonical_merge_names)
        conflict_entity: Entity | None = None
        # Direct name conflict
        if new_entity_name in existing_by_name and new_entity_name not in names_in_merge_set:
            conflict_entity = existing_by_name[new_entity_name]
        # Alias conflict
        if conflict_entity is None:
            for e in graph.entities:
                if e.name in names_in_merge_set:
                    continue
                try:
                    if any(
                        (a or "").strip().lower() == new_entity_name.strip().lower()
                        for a in e.aliases
                    ):
                        conflict_entity = e
                        break
                except Exception:
                    continue
        if conflict_entity is not None:
            raise ValueError(
                f"Entity named '{new_entity_name}' already exists (as a name or alias) and is not part of the merge set"
            )

        # Ensure all specified entities exist
        missing = [name for name in canonical_merge_names if name not in existing_by_name]
        if missing:
            raise ValueError(f"Entities not found: {', '.join(missing)}")

        # Gather entities to merge
        entities_to_merge = [existing_by_name[name] for name in canonical_merge_names]

        # Decide on entity_type: pick the most common among merged entities; fallback to first
        type_counts: dict[str, int] = {}
        for ent in entities_to_merge:
            type_counts[ent.entity_type] = type_counts.get(ent.entity_type, 0) + 1
        if type_counts:
            chosen_type = max(type_counts.items(), key=lambda kv: kv[1])[0]
        else:
            chosen_type = "unknown"

        # Merge and normalize observations, dedupe by content
        seen_contents: set[str] = set()
        merged_observations: list[Observation] = []
        for ent in entities_to_merge:
            for obs in ent.observations:
                if obs.content not in seen_contents:
                    seen_contents.add(obs.content)
                    merged_observations.append(obs)

        # If an entity exists with the target name and is in the merge list,
        # we will effectively replace it with the merged result. Remove all originals first.
        names_to_remove = set(canonical_merge_names)
        graph.entities = [e for e in graph.entities if e.name not in names_to_remove]

        # Rewrite relations to point to the new entity where applicable
        for rel in graph.relations:
            if rel.from_entity in names_to_remove:
                rel.from_entity = new_entity_name
            if rel.to_entity in names_to_remove:
                rel.to_entity = new_entity_name

        # Deduplicate relations after rewrite
        graph.relations = self._dedupe_relations_in_place(graph.relations)

        # Merge aliases: include all prior names and aliases, excluding the new name
        merged_aliases: set[str] = set()
        for ent in entities_to_merge:
            if ent.name.strip().lower() != new_entity_name.strip().lower():
                merged_aliases.add(ent.name)
            try:
                for a in ent.aliases:
                    if (
                        isinstance(a, str)
                        and a.strip()
                        and a.strip().lower() != new_entity_name.strip().lower()
                    ):
                        merged_aliases.add(a)
            except Exception:
                pass

        # Create and insert the new merged entity
        merged_entity = Entity(
            name=new_entity_name,
            entity_type=chosen_type,
            observations=merged_observations,
            aliases=sorted(merged_aliases),
        )
        graph.entities.append(merged_entity)

        await self._save_graph(graph)
        return merged_entity

    async def update_user_info(self, user_info: UserIdentifier) -> UserIdentifier:
        """
        Update the user's identifying information in the graph.
        """
        graph = await self._load_graph()
        graph.user_info = user_info
        await self._save_graph(graph)
        return user_info
