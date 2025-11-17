"""Core tests for KnowledgeGraphManager operations."""

import sys
import tempfile
from pathlib import Path

import pytest

# Ensure local src/ is importable without editable install
sys.path.insert(0, str((Path(__file__).parents[1] / "src").resolve()))

from mcp_knowledge_graph.manager import KnowledgeGraphManager
from mcp_knowledge_graph.models import (
    CreateEntityRequest,
    Observation,
    DurabilityType,
    CreateRelationRequest,
)


@pytest.mark.asyncio
async def test_create_entities_and_observations_and_search():
    with tempfile.TemporaryDirectory() as td:
        mem = Path(td) / "memory.jsonl"
        mgr = KnowledgeGraphManager(str(mem))

        # Create two entities
        results = await mgr.create_entities(
            [
                CreateEntityRequest(name="Alice", entity_type="person"),
                CreateEntityRequest(
                    name="Acme", entity_type="org", observations=[Observation.from_values("makes widgets", DurabilityType.LONG_TERM)]
                ),
            ]
        )
        # Expect 2 successes
        assert len(results) == 2
        assert all(r.errors is None for r in results)

        # Add relation by resolving IDs via names
        graph = await mgr.read_graph()
        alice = next(e for e in graph.entities if e.name == "Alice")
        acme = next(e for e in graph.entities if e.name == "Acme")

        rel_result = await mgr.create_relations(
            [
                CreateRelationRequest(
                    from_entity_id=alice.id,
                    to_entity_id=acme.id,
                    relation="works_at",
                )
            ]
        )
        assert len(rel_result.relations) == 1

        # Search should return both entities and the relation
        filtered = await mgr.search_nodes("Acme")
        assert any(e.name == "Acme" for e in filtered.entities)
        assert len(filtered.relations) == 1


@pytest.mark.asyncio
async def test_apply_observations_dedup_and_cleanup():
    with tempfile.TemporaryDirectory() as td:
        mem = Path(td) / "memory.jsonl"
        mgr = KnowledgeGraphManager(str(mem))

        # Create entity
        await mgr.create_entities([CreateEntityRequest(name="Bob", entity_type="person")])

        # Add duplicate observations
        from mcp_knowledge_graph.models import ObservationRequest

        results = await mgr.apply_observations(
            [
                ObservationRequest(
                    entity_name="Bob",
                    observations=[
                        Observation.from_values("likes pizza", DurabilityType.SHORT_TERM),
                        Observation.from_values("likes pizza", DurabilityType.SHORT_TERM),
                    ],
                )
            ]
        )
        # Only one unique observation added
        assert results and len(results[0].added_observations) == 1

        # Cleanup shouldn't remove fresh short-term observations
        cr = await mgr.cleanup_outdated_observations()
        assert cr.observations_removed_count == 0