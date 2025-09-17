"""
Knowledge Graph Manager with temporal observation support.

This module contains the core business logic for managing the knowledge graph,
including CRUD operations, temporal observation handling, and smart cleanup.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Annotated
from pathlib import Path
from uuid import uuid4
from .settings import Settings as settings, Logger as logger
from pydantic import Field

from .models import (
    Entity,
    EntityID,
    Relation,
    KnowledgeGraph,
    Observation,
    ObservationRequest,
    AddObservationResult,
    DeleteObservationRequest,
    CleanupResult,
    DurabilityGroupedObservations,
    DurabilityType,
    CreateRelationResult,
    CreateRelationRequest,
    CreateEntityRequest,
    CreateEntityResult,
    UserIdentifier,
    KnowledgeGraphException,
    MemoryRecord,
    GraphMeta,
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
        return cls(settings.memory_path)

    # ---------- Alias helpers ----------
    def _get_entity_by_name_or_alias(self, graph: KnowledgeGraph, identifier: str) -> Entity | None:
        """Return the first entity whose name or aliases match the identifier (case-insensitive). If no entity is found, returns None."""
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

    def _get_entity_by_id(self, graph: KnowledgeGraph, id: str) -> Entity | None:
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

    def _get_user_linked_entity(self, graph: KnowledgeGraph) -> Entity | None:
        """Return the user-linked entity if it exists. It should exist, so an error is raised if it doesn't."""
        if graph.user_info and graph.user_info.linked_entity_id:
            return self._get_entity_by_id(graph=graph, id=graph.user_info.linked_entity_id)
        else:
            raise KnowledgeGraphException("User-linked entity not found! This should not happen!")

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

    def _generate_new_valid_entity_id(self, graph: KnowledgeGraph) -> str:
        """Generate a unique new entity ID, ensuring it is not already in the graph. Entity IDs are UUID4s truncated to 8 characters. Convenience
        function for future proofing against changes in ID format."""
        while True:
            new_id = str(uuid4())[:8]
            if new_id not in [e.id for e in graph.entities]:
                break
        return new_id

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
        entities_list = graph.entities

        # Ensure the entity actually exists in the graph without mutating the list under iteration
        try:
            if entity not in entities_list:
                raise ValueError("entity not present in entities list")
        except Exception as e:
            raise KnowledgeGraphException(f"Entity {entity.name} must exist in graph: {e}")

        try:
            # Ensure the entity has a valid ID
            if entity.id in entities_list:
                logger.warning(f"Entity {entity.name} has a duplicate ID: {entity.id}")

            # Also make sure this isn't a copy of another with a different id
            # Compare against all other entities without mutating the source list
            others = [e for e in entities_list if e is not entity]
            other_entity_dicts = [e.model_dump(exclude_none=True, exclude={"id"}) for e in others]
            entity_no_id = entity.model_dump(exclude_none=True, exclude={"id"})
            for e_dict in other_entity_dicts:
                if e_dict == entity_no_id:
                    raise KnowledgeGraphException(
                        f"Entity {entity.id} is a duplicate of an existing entity"
                    )

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

    def _verify_relation(self, relation: Relation, graph: KnowledgeGraph) -> Relation:
        """
        Verify that the relation endpoints exist in the graph. If the entities themselves are
        required, use the _get_entities_from_relation() method instead.

        Args:
            relation: The Relation object to verify.
            graph: The graph to use to get the entities list.

        Returns:
            The relation with the endpoints validated.

        Raises:
            - ValueError if the relation is missing one or both endpoint IDs
            - RuntimeError if entity lookup fails with error
            - KnowledgeGraphException if entity lookup succeeds, but returns no results
        """
        graph = graph

        if not relation.from_id or not relation.to_id:
            raise ValueError(
                f"Relation `A {relation.relation} B` is missing one or both endpoint IDs!"
            )
        try:
            a = self._get_entity_by_id(graph, relation.from_id)
            b = self._get_entity_by_id(graph, relation.to_id)
        except Exception as e:
            raise RuntimeError(f"Error getting entities from relation: {e}")

        errors: list[str] = []
        if not a:
            errors.append(f"Invalid from ID: {str(relation.from_id)}")
        if not b:
            errors.append(
                KnowledgeGraphException(
                    f"Relation `{relation.relation}` has invalid endpoints: {relation.from_id} and {relation.to_id}"
                )
            )
        if len(errors) > 0:
            raise RuntimeError(f"Error verifying relation: {errors}")
        return relation

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
            from_entity = self._get_entity_by_id(graph, relation.from_id)
            to_entity = self._get_entity_by_id(graph, relation.to_id)

            return from_entity, to_entity
        except Exception as e:
            raise KnowledgeGraphException(f"Error getting entities from relation: {e}")

    def _get_relations_from_entities(
        self, entities: list[Entity], graph: KnowledgeGraph
    ) -> list[Relation]:
        """
        (Internal) Get the relations to and from each entity in a list of entities.
        """
        relations = []
        for entity in entities:
            try:
                for r in graph.relations:
                    if r.from_id == entity.id or r.to_id == entity.id:
                        relations.append(r)
            except Exception as e:
                logger.error(f"Error getting relations from entity {entity.name}: {e}")
                continue
        return relations

    async def get_relations_from_entities(self, entities: list[Entity]) -> list[Relation]:
        """
        Get the relations to and from each entity in a list of entities.
        """
        graph = await self._load_graph()
        return self._get_relations_from_entities(entities=entities, graph=graph)

    def _process_memory_line(self, line: str) -> UserIdentifier | Entity | Relation | None:
        """
        Produces a UserIdentifier, Entity, or Relation from a line of the memory file.

        Args:
            line: The line of the memory file to load

        Returns:
            The UserIdentifier, list of Entities, or list of Relations from the line
        """
        line = line.strip()
        if not line:
            return None

        # Determine line/record type via pydantic
        try:
            rec = MemoryRecord.model_validate_json(line)
            if rec.type == "meta":
                # meta is handled in _load_graph, ignore here
                return None
            if rec.type == "entity":
                return Entity.from_dict(rec.data)
            elif rec.type == "relation":
                return Relation.from_dict(rec.data)
            elif rec.type == "user_info":
                return UserIdentifier.from_dict(rec.data)
            else:
                raise ValueError(f"Missing or invalid type: {getattr(rec, 'type', None)}")
        except Exception as e:
            raise ValueError(f"Error parsing line: {e}")

    def _validate_user_info(
        self, graph: KnowledgeGraph, new_user_info: UserIdentifier | None = None
    ) -> UserIdentifier | None:
        """
        Validate the existing user info object of the knowledge graph, or a new user info object against the existing graph.

        Raises:
         - ValueError if the user info is invalid
         - KnowledgeGraphException if the user info appears valid, but the user-linked entity cannot be found

        Returns:
          - If a separate user info object is provided, returns the validated user info object
          - If no separate user info object is provided, returns None
        """
        if new_user_info:
            user_info = new_user_info
            separate_ui = True
        else:
            user_info = graph.user_info
            separate_ui = False

        user_info = new_user_info or graph.user_info
        entity_ids = [str(e.id) for e in graph.entities]

        if not user_info.preferred_name:
            raise ValueError("User info must have a preferred name")
        if not user_info.linked_entity_id:
            raise ValueError("User info must have a linked entity ID")

        if user_info.linked_entity_id not in entity_ids:
            raise KnowledgeGraphException(
                f"No entitiy found for user-linked entity ID `{user_info.linked_entity_id}`"
            )
        else:
            return user_info if separate_ui else None

    async def _load_graph(self) -> KnowledgeGraph:
        """
        Load the knowledge graph from JSONL storage.

        Returns:
            KnowledgeGraph loaded from file, or empty graph if file doesn't exist
        """
        logger.debug("manager._load_graph() called")
        if not self.memory_file_path.exists():
            logger.warning(
                f"⛔ Memory file not found at {self.memory_file_path}! Returning newly initialized graph."
            )
            new_graph = KnowledgeGraph.from_default()
            return new_graph

        # Load the graph
        try:
            # Instantiate graph components
            meta: GraphMeta | None = None
            user_info: UserIdentifier | None = None
            entities: list[Entity] = []
            relations: list[Relation] = []

            # Open the memory file
            with open(self.memory_file_path, "r", encoding="utf-8") as f:
                # Load the graph line by line
                for i, line in enumerate(f, start=1):
                    # Parse a MemoryRecord; on failure, log and continue
                    try:
                        rec = MemoryRecord.model_validate_json(line)
                    except Exception as e:
                        logger.warning(f"Skipping invalid line {i} in {self.memory_file_path}: {e}")
                        continue

                    if rec.type == "meta":
                        try:
                            meta = GraphMeta.model_validate(rec.data)
                        except Exception as e:
                            logger.warning(f"Invalid meta at line {i}: {e}; using defaults")
                            meta = GraphMeta()
                        continue

                    if rec.type == "user_info":
                        try:
                            user_info = UserIdentifier.from_dict(rec.data)
                        except Exception as e:
                            logger.warning(f"Invalid user_info at line {i}: {e}; skipping")
                        continue

                    if rec.type == "entity":
                        try:
                            entity = Entity.from_dict(rec.data)
                            entities.append(entity)
                        except Exception as e:
                            logger.warning(f"Invalid entity at line {i}: {e}; skipping")
                        continue

                    if rec.type == "relation":
                        try:
                            relation = Relation.from_dict(rec.data)
                            relations.append(relation)
                        except Exception as e:
                            logger.warning(f"Invalid relation at line {i}: {e}; skipping")
                        continue

                    logger.warning(f"Unknown record type '{rec.type}' at line {i}; skipping")

                    # Quick checks while streaming large files
                    if i > 50 and (len(entities) == 0 and len(relations) == 0 and not user_info):
                        raise RuntimeError(
                            "Failed to load graph: no valid data found in first 50 lines, memory is invalid or corrupt!"
                        )
                    if i > 500 and (len(entities) == 0 or len(relations) == 0 or not user_info):
                        raise RuntimeError(
                            "Failed to load graph: too much invalid data found in first 500 lines, memory is invalid or corrupt!"
                        )
                # EOF

            # If EOF is reached with no errors, begin validity checks
            if not user_info and not entities and not relations:
                raise KnowledgeGraphException("No valid data found in memory file!")

            # Ensure all components are present
            if not user_info:
                raise ValueError("No valid user info object found in memory file!")
            if not entities:
                raise KnowledgeGraphException("No valid entities found in memory file!")
            if not relations:
                raise KnowledgeGraphException("No valid relations found in memory file!")

            # Compose a preliminary graph
            graph = KnowledgeGraph(
                user_info=user_info, entities=entities, relations=relations, meta=meta
            )

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
            errors: list[Exception] = []
            try:
                # Validate entities
                valid_entities: list[Entity] = []
                for e in graph.entities:
                    try:
                        e = self._validate_entity(e, graph)
                    except Exception as err:
                        errors.append(
                            f"Bad entity `{str(e)[:24]}...`: {err}. Excluding from graph."
                        )
                    valid_entities.append(e)
                if len(errors) > 0 and len(valid_entities) > 0:
                    logger.error(
                        f"⚠️👤 Successfully validated {len(valid_entities)} entities, but {len(errors)} entities were invalid: {' \\ '.join(errors)}"
                    )
                elif len(errors) > 0 and len(valid_entities) == 0:
                    raise RuntimeError(
                        f"⛔👤 No valid entities in graph! Found {len(errors)} invalid entities: {' \\ '.join(errors)}"
                    )
                else:
                    logger.debug(f"✅👤 Successfully validated {len(valid_entities)} entities")

                # Validate relations
                valid_relations: list[Relation] = []
                relation_errors: list[str] = []
                for r in graph.relations:
                    try:
                        self._verify_relation(r, graph)
                    except Exception as e:
                        # Simply exclude relations that are invalid  TODO: handle more gracefully
                        relation_errors.append(
                            f"Bad relation `{str(r)[:24]}...`: {e}. Excluding from graph."
                        )
                        continue
                    valid_relations.append(r)
                if len(relation_errors) > 0 and len(valid_relations) > 0:
                    logger.error(
                        f"⚠️🔗 Successfully validated {len(valid_relations)} relations, but {len(relation_errors)} relations were invalid: {' \\ '.join(relation_errors)}"
                    )
                elif len(relation_errors) > 0 and len(valid_relations) == 0:
                    raise RuntimeError(
                        f"⛔🔗 No valid relations in graph! Found {len(relation_errors)} invalid relations: {' \\ '.join(relation_errors)}"
                    )
                else:
                    logger.debug(f"✅🔗 Successfully validated {len(valid_relations)} relations")

                # Verify the user-linked entity exists and is valid
                try:
                    self._validate_user_info(graph)
                    logger.debug("✅😃 Successfully validated user info!")
                except Exception as e:
                    raise RuntimeError(f"User info invalid: {e}")  # TODO: graceful fallback

            except RuntimeError as e:
                # Should exit with non-zero code if this happens
                raise RuntimeError(f"Critical validation error: {e}")
            except Exception as e:
                # Should validate the graph even if this happens
                errors.append(f"Unspecified validation error: {e}")

            # Validation complete! Recompose the fully-validated graph and return
            validated_graph = KnowledgeGraph.from_components(
                user_info=user_info, entities=valid_entities, relations=valid_relations
            )

            # Log that we have successfully loaded the graph components
            logger.debug(
                f"💾 Loaded user info for {user_info.preferred_name}; loaded {len(entities)} entities and {len(relations)} relations from memory file, validating..."
            )

            return validated_graph

        except Exception as e:
            raise RuntimeError("Error loading graph") from e

    async def _save_graph(self, graph: KnowledgeGraph) -> None:
        """
        Save the knowledge graph to JSONL storage.

        Args:
            graph: The knowledge graph to save

        For information on the format of the graph, see the README.md file.
        """
        logger.debug(f"manager._save_graph() called, saving to {self.memory_file_path}")
        # Note: Avoid calling cleanup here to prevent recursive save cycles.

        try:
            lines = []

            # Save meta / user info
            try:
                meta_payload = (graph.meta or GraphMeta()).model_dump(mode="json")
                lines.append(
                    json.dumps({"type": "meta", "data": meta_payload}, separators=(",", ":"))
                )
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

            logger.debug(f"💾 Successfully saved graph to {self.memory_file_path}")

        except Exception as e:
            logger.error(f"⛔ Failed to save graph: {e}")
            raise RuntimeError(f"⛔ Failed to save graph: {e}")

    async def _get_entity_id_map(self, graph: KnowledgeGraph) -> dict[EntityID, Entity]:
        """
        (Internal) Returns a map of entity IDs to entity names, including aliases.

        Map format: dict[EntityID(str), Entity]
        """
        if not graph.entities:
            raise ValueError("Invalid graph provided!")
        entities_list = graph.entities

        entity_id_map = {}
        for e in entities_list:
            if e.id:
                entity_id_map[e.id] = e
            else:
                logger.error(f"Entity {e.name} has no ID, skipping")

        return entity_id_map

    async def get_entity_id_map(
        self, graph: KnowledgeGraph | None = None
    ) -> dict[EntityID, Entity]:
        """
        Returns a map of entity IDs to entity objects from the provided knowledge graph or the default graph from the manager.
        """
        if graph is None:
            graph = await self._load_graph()
        return await self._get_entity_id_map(graph)

    async def create_entities(
        self, new_entities: list[CreateEntityRequest]
    ) -> list[CreateEntityResult]:
        """
        Validate and add multiple new entities to the knowledge graph.

        Args:
            entities: list of entities to add

        Returns:
            list of entities that were actually created (excludes existing names)
        """
        graph = await self._load_graph()

        # FIX: Create proper name-based lookups instead of ID-based lookups
        results: list[CreateEntityResult] = []
        
        # Create a lookup for existing entity names and aliases (case-insensitive)
        existing_names_lower = set()
        existing_aliases_lower = set()
        
        for entity in graph.entities:
            existing_names_lower.add(entity.name.lower().strip())
            try:
                for alias in entity.aliases or []:
                    if isinstance(alias, str) and alias.strip():
                        existing_aliases_lower.add(alias.lower().strip())
            except Exception:
                # Handle cases where aliases might not be a list
                pass

        # Process new entity requests
        for new_entity in new_entities:
            name_lc = (new_entity.name or "").strip().lower()
            
            if not name_lc:
                results.append(
                    CreateEntityResult(
                        entity=new_entity,
                        errors=["Entity name cannot be empty"],
                    )
                )
                continue

            # Check if the entity already exists by name or alias
            if name_lc in existing_names_lower or name_lc in existing_aliases_lower:
                # Find the existing entity for better error message
                existing_entity = None
                for entity in graph.entities:
                    if entity.name.lower().strip() == name_lc:
                        existing_entity = entity
                        break
                    try:
                        for alias in entity.aliases or []:
                            if isinstance(alias, str) and alias.lower().strip() == name_lc:
                                existing_entity = entity
                                break
                    except Exception:
                        pass
                    if existing_entity:
                        break
                
                if existing_entity:
                    results.append(
                        CreateEntityResult(
                            entity=new_entity,
                            errors=[
                                f'Entity "{new_entity.name}" already exists as "{existing_entity.name}" ({existing_entity.id}); skipped'
                            ],
                        )
                    )
                else:
                    results.append(
                        CreateEntityResult(
                            entity=new_entity,
                            errors=[f'Entity "{new_entity.name}" already exists; skipped'],
                        )
                    )
                continue

            # If not existing, create the entity
            try:
                entity = Entity.from_values(
                    name=new_entity.name,
                    entity_type=new_entity.entity_type,
                    observations=new_entity.observations or [],
                    aliases=new_entity.aliases or [],
                    icon=new_entity.icon,
                    id=self._generate_new_valid_entity_id(graph),
                )
                
                # Add the entity to the graph
                graph.entities.append(entity)
                
                # Add to existing lookups to prevent duplicates in this batch
                existing_names_lower.add(entity.name.lower().strip())
                try:
                    for alias in entity.aliases or []:
                        if isinstance(alias, str) and alias.strip():
                            existing_aliases_lower.add(alias.lower().strip())
                except Exception:
                    pass
                
                # Add the success to the results
                results.append(
                    CreateEntityResult(entity=entity, errors=None)
                )
            except Exception as e:
                results.append(
                    CreateEntityResult(
                        entity=new_entity,
                        errors=[f"Failed to create entity: {str(e)}"],
                    )
                )
        # Save the graph only if there were successful creations
        successful_creations = [r for r in results if not r.errors]
        if successful_creations:
            try:
                await self._save_graph(graph)
            except Exception as exc:
                # If save fails, mark all successful creations as failed
                for result in successful_creations:
                    result.errors = [f"Failed to save graph: {str(exc)}"]
                raise RuntimeError(f"Failed to save graph during entity addition: {exc}")

        return results

    async def create_relations(
        self, relations: list[CreateRelationRequest]
    ) -> CreateRelationResult:
        """
        Create multiple new relations between entities.

        Args:
            relations: list of relations to create

        Returns:
            list of relations that were actually created (excludes duplicates)
        """
        graph = await self._load_graph()

        valid_relations: list[Relation] = []
        for r in relations:
            errors: list[str] = []
            try:
                if not r.from_entity_id:
                    from_entity = self._get_entity_by_name_or_alias(graph, r.from_entity_name)
                else:
                    from_entity = self._get_entity_by_id(graph, r.from_entity_id)
            except Exception as e:
                errors.append(f"Error matching 'from' entity to relation endpoint: {e}")

            try:
                if not r.to_entity_id:
                    to_entity = self._get_entity_by_name_or_alias(graph, r.to_entity_name)
                else:
                    to_entity = self._get_entity_by_id(graph, r.to_entity_id)

            except Exception as e:
                errors.append(f"Error matching 'to' entity to relation endpoint: {e}")

            if errors:
                logger.error(f"Error adding relation: {', '.join(errors)}. Skipping.")
                continue
            else:
                new_relation = Relation.from_entities(from_entity, to_entity, r.relation)
                valid_relations.append(new_relation)

        if not valid_relations:
            raise KnowledgeGraphException("No valid relations to add!")

        # Add valid relations to the graph
        succeeded_rels: list[Relation] = []
        for r in valid_relations:
            try:
                graph.relations.append(r)
                succeeded_rels.append(r)
            except Exception as e:
                logger.error(f"Error adding relation: {e}")
                continue

        await self._save_graph(graph)
        return CreateRelationResult(relations=succeeded_rels)

    async def apply_observations(
        self, requests: list[ObservationRequest]
    ) -> list[AddObservationResult]:
        """
        Add new observations to existing entities.

        Args:
            requests: list of observation addition requests

        Returns:
            list of results showing what was actually added, and/or any errors that occurred

        Raises:
            ValueError: If an entity is not found
        """
        graph = await self._load_graph()
        results: list[AddObservationResult] = []

        for request in requests:
            # Resolve entity by ID first, else by name/alias; support 'user' shortcut in name
            try:
                if request.entity_id:
                    entity = self._get_entity_by_id(graph, request.entity_id)
                elif request.entity_name:
                    name = (request.entity_name or "").strip()
                    if (
                        name.lower() in {"user", "__user__"}
                        and graph.user_info
                        and graph.user_info.linked_entity_id
                    ):
                        entity = self._get_entity_by_id(graph, graph.user_info.linked_entity_id)
                    else:
                        entity = self._get_entity_by_name_or_alias(graph, name)

                # If we didn't find an entity, append an error to the results and continue
                if not entity:
                    results.append(
                        AddObservationResult(
                            entity=entity,
                            errors=[
                                f"Entity not found for request (name='{request.entity_name}', id='{request.entity_id}')"
                            ],
                        )
                    )
                    continue

            # If we encountered an error, append an error to the results and continue
            except Exception as e:
                (
                    results.append(
                        AddObservationResult(
                            entity=entity,
                            errors=[f"Error resolving entity to add observations: {e}"],
                        )
                    ),
                )
                continue

            # Create observations with timestamps from the request

            observations: list[str] = [old_obs.content for old_obs in entity.observations] or []
            new_observations: list[Observation] = []
            for o in request.observations:
                obs = Observation.from_values(o.content, o.durability)
                # Avoid duplicates
                if obs.content not in observations:
                    new_observations.append(obs)
            else:
                new_observations.append(obs)
            entity.observations.extend(new_observations)

            try:
                results.append(
                    AddObservationResult(entity=entity, added_observations=new_observations)
                )
            except Exception as e:
                results.append(
                    AddObservationResult(
                        entity=entity, errors=[f"Error appending observations to entity: {e}"]
                    )
                )
                continue

        await self._save_graph(graph)
        return results

    async def get_entity_by_id(self, entity_id: str) -> Entity | None:
        """
        Get an entity by its ID. Returns None if no entity is found.
        """
        graph = await self._load_graph()
        return self._get_entity_by_id(graph, entity_id)

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

    async def delete_entities(
        self, entity_names: list[str] | None = None, entity_ids: list[str] | None = None
    ) -> None:
        """
        Delete multiple entities and their associated relations.

        Args:
            entity_names: list of entity names to delete
            entity_ids: list of entity IDs to delete

            If both entity_names and entity_ids are provided, both will be used to delete the entities.
        """
        try:
            entities_to_delete: list[Entity] = []
            graph = await self._load_graph()
            if entity_names:
                for name in entity_names:
                    entity = self._get_entity_by_name_or_alias(graph, name)
                    if entity:
                        entities_to_delete.append(entity)
            if entity_ids:
                for id in entity_ids:
                    entity = self._get_entity_by_id(graph, id)
                    if entity:
                        entities_to_delete.append(entity)
            if not entities_to_delete:
                raise ValueError("No valid data provided")

            # Delete the entities
            graph.entities = [e for e in graph.entities if e not in entities_to_delete]

            # Remove relations involving deleted entities
            new_relations: list[Relation] = []
            for r in graph.relations:
                from_e, to_e = self._get_entities_from_relation(r, graph)
                if from_e not in entities_to_delete and to_e not in entities_to_delete:
                    new_relations.append(r)
            graph.relations = new_relations
        except Exception as e:
            raise KnowledgeGraphException(f"Error deleting entities: {e}")

        # If no errors, save the graph
        await self._save_graph(graph)

    async def delete_observations(self, deletions: list[DeleteObservationRequest]) -> None:
        """
        Delete specific observations from entities.

        Args:
            deletions: list of observation deletion requests
        """
        graph = await self._load_graph()

        for deletion in deletions:
            # Resolve entity by ID first, else by name/alias; support 'user' shortcut in name
            entity: Entity | None = None
            try:
                if getattr(deletion, "entity_id", None):
                    entity = self._get_entity_by_id(graph, deletion.entity_id)  # type: ignore[arg-type]
                if entity is None:
                    name = (deletion.entity_name or "").strip()
                    if (
                        name.lower() in {"user", "__user__"}
                        and graph.user_info
                        and graph.user_info.linked_entity_id
                    ):
                        entity = self._get_entity_by_id(graph, graph.user_info.linked_entity_id)
                    else:
                        entity = self._get_entity_by_name_or_alias(graph, name)
            except Exception as e:
                logger.error(f"Error resolving entity for deletion: {e}")
                entity = None

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

        # Build a set of (from_id, to_id, relation) tuples to delete; resolve by names if needed
        to_delete: set[tuple[str, str, str]] = set()
        for rel in relations:
            from_id = rel.from_id
            to_id = rel.to_id
            if not from_id and rel.from_entity:
                ent = self._get_entity_by_name_or_alias(graph, rel.from_entity)
                from_id = ent.id if ent else None
            if not to_id and rel.to_entity:
                ent = self._get_entity_by_name_or_alias(graph, rel.to_entity)
                to_id = ent.id if ent else None
            if from_id and to_id and rel.relation:
                to_delete.add((from_id, to_id, rel.relation))

        graph.relations = [
            r for r in graph.relations if (r.from_id, r.to_id, r.relation) not in to_delete
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

        # Filter relations using IDs of filtered entities
        filtered_entity_ids = {entity.id for entity in filtered_entities if entity.id}
        filtered_relations = [
            r
            for r in graph.relations
            if r.from_id in filtered_entity_ids and r.to_id in filtered_entity_ids
        ]

        return KnowledgeGraph(
            user_info=graph.user_info,
            entities=filtered_entities,
            relations=filtered_relations,
        )

    async def open_nodes(
        self,
        ids: list[EntityID] | None = None,
        names: list[str] | str | None = None,
        # include_observations: bool = True,
        # include_relations: bool = True,
    ) -> list[Entity]:
        """
        Open specific nodes (entities) in the knowledge graph by their names or IDs.
        If both names and ids are provided, both will be used to filter the entities.

        Args:
            ids: list of entity IDs to retrieve
            names: list of entity names to retrieve

        Returns:

            A list of entities that match the provided names or IDs.
        """
        graph = await self._load_graph()
        user_info = graph.user_info
        if not ids and not names:
            raise ValueError("Either ids or names must be provided")

        
        # Check if ids is a string representation of a list
        resolved_ids: list[str] = []
        if ids is not None:
            if isinstance(ids, str):
                logger.debug(f"DEBUG: ids is a string, attempting to parse: {ids}")
                try:
                    # Try to parse as JSON first (for string representations of lists)
                    parsed = json.loads(ids)
                    if isinstance(parsed, list):
                        resolved_ids = [str(item) for item in parsed]
                        logger.debug(f"open_nodes: parsed ids as JSON list: {resolved_ids}")
                    else:
                        resolved_ids = [ids]
                        logger.debug(f"open_nodes: treating ids as single string: {resolved_ids}")
                except (json.JSONDecodeError, ValueError):
                    # If JSON parsing fails, treat as single string
                    resolved_ids = [ids]
                    logger.debug(f"open_nodes: JSON parsing failed, treating as single string: {resolved_ids}")
            elif isinstance(ids, list):
                # Handle case where list contains JSON-encoded strings
                for id_item in ids:
                    if id_item is None:
                        continue
                    id_str = str(id_item)
                    try:
                        # Try to parse each item as JSON in case it's a JSON-encoded list
                        parsed = json.loads(id_str)
                        if isinstance(parsed, list):
                            resolved_ids.extend([str(item) for item in parsed])
                        else:
                            resolved_ids.append(id_str)
                    except (json.JSONDecodeError, ValueError):
                        # If JSON parsing fails, treat as regular string
                        resolved_ids.append(id_str)
                logger.debug(f"open_nodes: ids received as a list, resolved to: {resolved_ids}")

        # Check if names is a string representation of a list
        resolved_names: list[str] = []
        if names is not None:
            if isinstance(names, str):
                try:
                    # Try to parse as JSON first (for string representations of lists)
                    parsed = json.loads(names)
                    if isinstance(parsed, list):
                        resolved_names = [str(item) for item in parsed]
                    else:
                        resolved_names = [names]
                except (json.JSONDecodeError, ValueError):
                    # If JSON parsing fails, treat as single string
                    resolved_names = [names]
            elif isinstance(names, list):
                # Handle case where list contains JSON-encoded strings
                for name_item in names:
                    if name_item is None:
                        continue
                    name_str = str(name_item)
                    try:
                        # Try to parse each item as JSON in case it's a JSON-encoded list
                        parsed = json.loads(name_str)
                        if isinstance(parsed, list):
                            resolved_names.extend([str(item) for item in parsed])
                        else:
                            resolved_names.append(name_str)
                    except (json.JSONDecodeError, ValueError):
                        # If JSON parsing fails, treat as regular string
                        resolved_names.append(name_str)

        opened_nodes: list[Entity] = []

        # Get the entities that match the provided names
        try:
            if resolved_names and len(resolved_names) > 0:
                logger.debug(f"Getting entities by names: {resolved_names}")
                for ident in resolved_names:
                    if not ident or not isinstance(ident, str):
                        logger.warning(f"Skipping invalid identifier: {ident}")
                        continue
                        
                    # Special case for user
                    logger.debug(f"Getting entity: {ident}")
                    if ident.lower() in {"user", "__user__"} and user_info and user_info.linked_entity_id:
                        try:
                            entity = self._get_user_linked_entity(graph=graph)
                            if entity:
                                opened_nodes.append(entity)
                            else:
                                logger.error(f"User-linked entity not found for identifier: {ident}")
                        except Exception as e:
                            logger.error(f"Error getting user-linked entity for {ident}: {e}")
                    else:
                        entity = self._get_entity_by_name_or_alias(graph, ident)
                        if entity:
                            opened_nodes.append(entity)
                        else:
                            logger.error(f"Entity not found: {ident}")
        except Exception as e:
            logger.error(f"Error getting entities by names: {e}")
            raise ValueError(f"Error getting entities by names: {e}")

        # Get the entities that match the provided IDs
        try:
            if resolved_ids and len(resolved_ids) > 0:
                logger.debug(f"Getting entities by IDs: {resolved_ids}")
                for entity_id in resolved_ids:
                    if not entity_id:
                        logger.warning(f"Skipping empty ID: {entity_id}")
                        continue
                        
                    entity = self._get_entity_by_id(graph, str(entity_id))
                    if entity:
                        opened_nodes.append(entity)
                    else:
                        logger.error(f"Entity not found for ID: {entity_id}")
        except Exception as e:
            logger.error(f"Error getting entities by IDs: {e}")
            raise ValueError(f"Error getting entities by IDs: {e}")

        # Remove duplicates while preserving order
        seen = set()
        result = []
        for entity in opened_nodes:
            if entity.id not in seen:
                seen.add(entity.id)
                result.append(entity)

        return result

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

        # Create and insert the new merged entity, ensuring a unique ID
        merged_entity = Entity(
            name=new_entity_name,
            entity_type=chosen_type,
            observations=merged_observations,
            aliases=sorted(merged_aliases),
        )
        merged_entity = self._validate_new_entity_id(merged_entity, graph)
        graph.entities.append(merged_entity)

        # Rewrite relations to point to the new entity where applicable (by IDs)
        ids_to_rewrite = {
            existing_by_name[name].id for name in names_to_remove if existing_by_name[name].id
        }
        for rel in graph.relations:
            if rel.from_id in ids_to_rewrite:
                rel.from_id = merged_entity.id
            if rel.to_id in ids_to_rewrite:
                rel.to_id = merged_entity.id

        # Deduplicate relations after rewrite by (from_id, to_id, relation)
        dedup: dict[tuple[str, str, str], Relation] = {}
        for rel in graph.relations:
            key = (rel.from_id, rel.to_id, rel.relation)
            dedup[key] = rel
        graph.relations = list(dedup.values())

        await self._save_graph(graph)
        return merged_entity

    async def get_user_info(self) -> UserIdentifier:
        """
        Get the user info from the graph.
        """
        graph = await self._load_graph()
        return graph.user_info

    async def update_user_info(self, new_user_info: UserIdentifier) -> UserIdentifier:
        """Update the user's identifying information in the graph.
        Accepts a fully-formed `UserIdentifier` which will be validated against the current graph.
        """
        graph = await self._load_graph()
        try:
            validated = self._validate_user_info(graph, new_user_info)
        except Exception as e:
            raise KnowledgeGraphException(f"New user info invalid: {e}")
        graph.user_info = validated
        await self._save_graph(graph)
        return validated

    async def update_entity(
        self,
        identifier: str | None = None,
        entity_id: str | None = None,
        name: str | None = None,
        entity_type: str | None = None,
        aliases: list[str] | None = None,
        icon: str | None = None,
        merge_aliases: bool = True,
    ) -> Entity:
        """
        Update mutable properties of a single entity.

        Args:
            identifier: Canonical name or alias of the entity to update. Used if entity_id not provided.
            entity_id: ID of the entity to update. Takes precedence over identifier when provided.
            name: New canonical name for the entity
            entity_type: New type for the entity
            aliases: Aliases to add or replace (based on merge_aliases)
            icon: New emoji icon. Use empty string to clear
            merge_aliases: When True, merge provided aliases into existing list; when False, replace list

        Returns:
            The updated Entity

        Raises:
            KnowledgeGraphException or ValueError on invalid input or conflicts
        """
        graph = await self._load_graph()

        # Locate entity
        target: Entity | None = None
        try:
            if entity_id:
                target = self._get_entity_by_id(graph, entity_id)
            else:
                if not identifier:
                    raise ValueError("Either entity_id or identifier is required")
                target = self._get_entity_by_name_or_alias(graph, identifier)
        except Exception as e:
            raise KnowledgeGraphException(f"Error locating entity: {e}")

        if not target:
            raise ValueError("Entity not found")

        # Build fast lookups excluding the target entity
        other_entities = [e for e in graph.entities if e is not target]
        existing_names_lc = {e.name.strip().lower() for e in other_entities}
        existing_aliases_lc: set[str] = set()
        for e in other_entities:
            try:
                for a in e.aliases or []:
                    if isinstance(a, str):
                        existing_aliases_lc.add(a.strip().lower())
            except Exception:
                pass

        # Apply name change
        if name is not None:
            new_name = (name or "").strip()
            if not new_name:
                raise ValueError("Entity name must not be empty")
            # Prevent conflicts with other entities' names or aliases
            if (
                new_name.strip().lower() in existing_names_lc
                or new_name.strip().lower() in existing_aliases_lc
            ):
                raise KnowledgeGraphException(
                    f"Cannot rename entity to '{new_name}': name conflicts with an existing entity or alias"
                )
            target.name = new_name

        # Apply type change
        if entity_type is not None:
            new_type = (entity_type or "").strip()
            if not new_type:
                raise ValueError("Entity type must not be empty")
            target.entity_type = new_type

        # Apply icon change
        if icon is not None:
            # Allow clearing by empty string
            target.icon = icon

        # Apply alias updates
        if aliases is not None:
            # Normalize provided aliases
            normalized_incoming: list[str] = [str(a).strip() for a in aliases if str(a).strip()]

            # Ensure no incoming alias conflicts with other entities' canonical names or aliases
            for a in normalized_incoming:
                a_lc = a.lower()
                if a_lc in existing_names_lc or a_lc in existing_aliases_lc:
                    raise KnowledgeGraphException(
                        f"Cannot set alias '{a}': conflicts with an existing entity or alias"
                    )

            if merge_aliases:
                merged: list[str] = []
                seen: set[str] = set()
                # Start with current aliases
                for a in target.aliases or []:
                    a_norm = (a or "").strip()
                    if not a_norm:
                        continue
                    a_lc = a_norm.lower()
                    if a_lc not in seen:
                        seen.add(a_lc)
                        merged.append(a_norm)
                # Add incoming
                for a in normalized_incoming:
                    a_lc = a.lower()
                    if a_lc not in seen:
                        seen.add(a_lc)
                        merged.append(a)
                target.aliases = [a for a in merged if a.lower() != target.name.strip().lower()]
            else:
                # Replace aliases entirely
                target.aliases = [
                    a for a in normalized_incoming if a.lower() != target.name.strip().lower()
                ]

        # Final validation step for updated entity
        try:
            self._validate_entity(target, graph)
        except Exception as e:
            raise KnowledgeGraphException(f"Updated entity failed validation: {e}")

        # Persist changes
        await self._save_graph(graph)
        return target
