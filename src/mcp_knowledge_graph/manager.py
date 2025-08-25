"""
Knowledge Graph Manager with temporal observation support.

This module contains the core business logic for managing the knowledge graph,
including CRUD operations, temporal observation handling, and smart cleanup.
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from pathlib import Path
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
            key = (rel.from_entity, rel.to_entity, rel.relation_type)
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

    async def _load_graph(self) -> KnowledgeGraph:
        """
        Load the knowledge graph from JSONL storage.

        Returns:
            KnowledgeGraph loaded from file, or empty graph if file doesn't exist
        """
        if not self.memory_file_path.exists():
            logger.warning(
                f"⛔ Memory file not found at {self.memory_file_path}! Returning empty graph."
            )
            return KnowledgeGraph(), True
        else:
            logger.info(f"📈 Loaded graph from {self.memory_file_path}")

        user_info_missing: bool = False
        try:
            user_info: UserIdentifier | None = None
            entities = []
            relations = []

            with open(self.memory_file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        break

                    try:
                        item = json.loads(line)

                        item_type = item.get("type")

                        payload: dict | None = None
                        if item_type in ("entity", "relation", "user_info"):
                            if isinstance(item.get("data"), dict):
                                payload = item["data"]
                                if not payload:
                                    raise logger.error(f"Invalid payload: {item}")
                            else:
                                raise logger.error(f"{item} has invalid item type: {item_type}")

                        if item_type == "entity" and isinstance(payload, dict):
                            entity = Entity(**payload)
                            entities.append(entity)

                        elif item_type == "relation" and isinstance(payload, dict):
                            relations.append(Relation(**payload))

                        elif item_type == "user_info" and isinstance(payload, dict):
                            user_info_missing = (
                                payload.get("preferred_name") == "default_user" 
                                or payload.get("preferred_name") == "__default_user__"
                                or payload.get("first_name") == "default_user"
                                or payload.get("first_name") == "__default_user__"
                            )
                            if not user_info_missing:
                                try:
                                    user_info = UserIdentifier(**payload)
                                except Exception as e:
                                    raise RuntimeError(f"Error parsing user info from memory file: {e}")
                            logger.debug(f"Loaded user info: {payload}")

                        else:
                            # Unrecognized line; skip with warning but continue
                            logger.warning(
                                f"Warning: Skipping unrecognized line in {self.memory_file_path}: Missing or invalid type/payload"
                            )
                            continue
                    except (json.JSONDecodeError, ValueError, TypeError) as e:
                        # Skip invalid lines but continue processing
                        logger.warning(
                            f"Warning: Skipping invalid line in {self.memory_file_path}: {e}"
                        )
                        continue

            if not user_info:
                logger.warning("No valid user info object found in memory file! Initializing new user info object with default user info.")
                user_info = UserIdentifier.from_default()
                user_info_missing = True

            logger.info(f"💾 Loaded {len(entities)} entities and {len(relations)} relations from memory file")
            return KnowledgeGraph(user_info=user_info, entities=entities, relations=relations)

        except Exception as e:
            raise RuntimeError(f"Error loading graph: {e}")

    async def _save_graph(self, graph: KnowledgeGraph, test: bool = False) -> None:
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
            if graph.user_info:
                user_info_payload = graph.user_info.model_dump()
                record = {"type": "user_info", "data": user_info_payload}
                lines.append(json.dumps(record, separators=(",", ":")))
            else:
                # If for some reason the user info is not set, save with default info
                user_info_payload = UserIdentifier.from_default().model_dump()
                record = {"type": "user_info", "data": user_info_payload}
                lines.append(json.dumps(record, separators=(",", ":")))

            # Save entities
            for entity in graph.entities:
                entity_payload = entity.model_dump()
                record = {"type": "entity", "data": entity_payload}
                lines.append(json.dumps(record, separators=(",", ":")))

            # Save relations
            for relation in graph.relations:
                relation_payload = relation.model_dump()
                record = {"type": "relation", "data": relation_payload}
                lines.append(json.dumps(record, separators=(",", ":")))

            if test:
                memory_file_path = self.memory_file_path.with_suffix("_test.jsonl")
            else:
                memory_file_path = self.memory_file_path
            with open(memory_file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

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
        graph, _ = await self._load_graph()
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
        graph, _ = await self._load_graph()

        # Canonicalize endpoints to entity names if aliases provided
        canonicalized: list[Relation] = []
        for rel in relations:
            from_c = self._canonicalize_entity_name(graph, rel.from_entity)
            to_c = self._canonicalize_entity_name(graph, rel.to_entity)
            canonicalized.append(
                Relation(from_entity=from_c, to_entity=to_c, relation_type=rel.relation_type)
            )

        # Create set of existing relations for duplicate checking (with canonical names)
        existing_relations = {
            (r.from_entity, r.to_entity, r.relation_type) for r in graph.relations
        }

        new_relations = [
            relation
            for relation in canonicalized
            if (relation.from_entity, relation.to_entity, relation.relation_type)
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
        graph, _ = await self._load_graph()
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

    async def cleanup_outdated_observations(self) -> CleanupResult:
        """
        Remove observations that are likely outdated based on durability and age.

        Returns:
            CleanupResult with details of what was removed
        """
        graph, _ = await self._load_graph()
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
        graph, _ = await self._load_graph()
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

        graph, _ = await self._load_graph()
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
        graph, _ = await self._load_graph()

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
        graph, _ = await self._load_graph()

        # Canonicalize relation endpoints before building deletion set
        canonical_to_delete = {
            (
                self._canonicalize_entity_name(graph, r.from_entity),
                self._canonicalize_entity_name(graph, r.to_entity),
                r.relation_type,
            )
            for r in relations
        }

        # Filter out matching relations
        graph.relations = [
            r
            for r in graph.relations
            if (r.from_entity, r.to_entity, r.relation_type) not in canonical_to_delete
        ]

        await self._save_graph(graph)

    async def read_graph(self) -> tuple[KnowledgeGraph, bool]:
        """
        Read the entire knowledge graph.

        Returns:
            The complete knowledge graph
        """
        graph, user_info_missing = await self._load_graph()
        return graph, user_info_missing

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

        return KnowledgeGraph(entities=filtered_entities, relations=filtered_relations)

    async def open_nodes(self, names: list[str]) -> KnowledgeGraph:
        """
        Open specific nodes in the knowledge graph by their names.

        Args:
            names: list of entity names to retrieve

        Returns:
            Knowledge graph containing only the specified entities and their relations
        """
        graph = await self._load_graph()
        # Resolve identifiers to canonical names that exist in the graph
        names_set: set[str] = set()
        for ident in names:
            entity = self._get_entity_by_name_or_alias(graph, ident)
            if entity:
                names_set.add(entity.name)

        # Filter entities by name
        filtered_entities = [e for e in graph.entities if e.name in names_set]

        # Filter relations between the specified entities
        filtered_relations = [
            r for r in graph.relations if r.from_entity in names_set and r.to_entity in names_set
        ]

        return KnowledgeGraph(entities=filtered_entities, relations=filtered_relations)

    async def merge_entities(self, new_entity_name: str, entity_names: list[str]) -> Entity:
        """
        Merge multiple entities into a new entity with the provided name.

        - Combines observations from all entities being merged, normalizing to
          timestamped observations and deduplicating by content.
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
        graph, _ = await self._load_graph()
        graph.user_info = user_info
        await self._save_graph(graph)
        return user_info