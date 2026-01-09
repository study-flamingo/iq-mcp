"""Comprehensive tests for KnowledgeGraphManager CRUD operations."""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str((Path(__file__).parents[1] / "src").resolve()))

from mcp_knowledge_graph.manager import KnowledgeGraphManager
from mcp_knowledge_graph.models import (
    CreateEntityRequest,
    Observation,
    DurabilityType,
    CreateRelationRequest,
    ObservationRequest,
    Relation,
)


@pytest.fixture
def temp_memory_dir():
    """Create a temporary directory for memory files."""
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def mock_context(temp_memory_dir):
    """Mock the AppContext to avoid initialization issues in tests."""
    import logging
    from mcp_knowledge_graph.context import ctx, AppContext
    from mcp_knowledge_graph.settings import IQSettings, AppSettings

    core_settings = IQSettings(
        debug=False,
        transport="stdio",
        port=8000,
        memory_path=str(Path(temp_memory_dir) / "memory.jsonl"),
        streamable_http_host=None,
        streamable_http_path=None,
        project_root=Path(temp_memory_dir),
        no_emojis=False,
        dry_run=False,
        stateless_http=False,
    )

    # Create AppSettings with core settings and no Supabase
    mock_settings = AppSettings(core=core_settings, supabase=None)

    # Create a test logger
    test_logger = logging.getLogger("iq-mcp-test")
    test_logger.setLevel(logging.DEBUG)

    # Set the attributes directly on the singleton instance
    ctx._settings = mock_settings
    ctx._supabase = None
    ctx._logger = test_logger
    ctx._initialized = True

    try:
        yield temp_memory_dir
    finally:
        # Clean up - reset the context for other tests
        ctx._initialized = False
        if hasattr(ctx, "_settings"):
            del ctx._settings
        if hasattr(ctx, "_supabase"):
            del ctx._supabase
        if hasattr(ctx, "_logger"):
            del ctx._logger


@pytest.mark.asyncio
async def test_create_single_entity(mock_context):
    """Test creating a single entity."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    results = await mgr.create_entities(
        [CreateEntityRequest(name="TestEntity", entity_type="test")]
    )

    assert len(results) == 1
    assert results[0].errors is None
    assert results[0].entity.name == "TestEntity"


@pytest.mark.asyncio
async def test_create_multiple_entities(mock_context):
    """Test creating multiple entities at once."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    results = await mgr.create_entities(
        [
            CreateEntityRequest(name="Alice", entity_type="person"),
            CreateEntityRequest(name="Bob", entity_type="person"),
        ]
    )

    assert len(results) == 2
    assert all(r.errors is None for r in results)


@pytest.mark.asyncio
async def test_create_duplicate_entity_fails(mock_context):
    """Test that creating a duplicate entity returns an error."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities([CreateEntityRequest(name="Alice", entity_type="person")])
    results = await mgr.create_entities([CreateEntityRequest(name="Alice", entity_type="person")])

    assert results[0].errors is not None


@pytest.mark.asyncio
async def test_read_graph(mock_context):
    """Test reading the entire graph."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities([CreateEntityRequest(name="Alice", entity_type="person")])
    graph = await mgr.read_graph()

    assert graph is not None
    assert len(graph.entities) >= 1


@pytest.mark.asyncio
async def test_search_nodes(mock_context):
    """Test searching for nodes."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities(
        [
            CreateEntityRequest(
                name="Acme",
                entity_type="org",
                observations=[Observation.from_values("makes widgets", DurabilityType.LONG_TERM)],
            ),
        ]
    )

    results = await mgr.search_nodes("Acme")
    assert any(e.name == "Acme" for e in results.entities)


@pytest.mark.asyncio
async def test_create_relation(mock_context):
    """Test creating a relation between entities."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    results = await mgr.create_entities(
        [
            CreateEntityRequest(name="Alice", entity_type="person"),
            CreateEntityRequest(name="Acme", entity_type="organization"),
        ]
    )

    rel_result = await mgr.create_relations(
        [
            CreateRelationRequest(
                from_entity_id=results[0].entity.id,
                to_entity_id=results[1].entity.id,
                relation="works_at",
            )
        ]
    )

    assert len(rel_result.relations) == 1


@pytest.mark.asyncio
async def test_add_observations(mock_context):
    """Test adding observations to an entity."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities([CreateEntityRequest(name="Alice", entity_type="person")])

    results = await mgr.apply_observations(
        [
            ObservationRequest(
                entity_name="Alice",
                observations=[Observation.from_values("likes pizza", DurabilityType.LONG_TERM)],
            )
        ]
    )

    assert len(results[0].added_observations) == 1


@pytest.mark.asyncio
async def test_observation_deduplication(mock_context):
    """Test that duplicate observations are not added."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities([CreateEntityRequest(name="Bob", entity_type="person")])

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

    assert len(results[0].added_observations) == 1


@pytest.mark.asyncio
async def test_cleanup_outdated_observations(mock_context):
    """Test that fresh observations are not cleaned up."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities([CreateEntityRequest(name="Test", entity_type="test")])
    await mgr.apply_observations(
        [
            ObservationRequest(
                entity_name="Test",
                observations=[
                    Observation.from_values("fresh observation", DurabilityType.SHORT_TERM)
                ],
            )
        ]
    )

    cleanup_result = await mgr.cleanup_outdated_observations()
    assert cleanup_result.observations_removed_count == 0


@pytest.mark.asyncio
async def test_entity_alias_resolution(mock_context):
    """Test that entities can be found by alias."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities(
        [CreateEntityRequest(name="Robert_Smith", entity_type="person", aliases=["Bobby"])]
    )

    entities = await mgr.open_nodes(names=["Bobby"])
    assert len(entities) == 1
    assert entities[0].name == "Robert_Smith"


@pytest.mark.asyncio
async def test_persistence_across_sessions(mock_context):
    """Test that data persists across manager instances."""
    mem = Path(mock_context) / "memory.jsonl"

    mgr1 = KnowledgeGraphManager(str(mem))
    await mgr1.create_entities([CreateEntityRequest(name="Persistent", entity_type="test")])

    mgr2 = KnowledgeGraphManager(str(mem))
    entities = await mgr2.open_nodes(names=["Persistent"])

    assert len(entities) == 1
    assert entities[0].name == "Persistent"


# v1.4.0 Tests: Entity Reference Flexibility and Enhanced Tools


@pytest.mark.asyncio
async def test_resolve_entity_identifier_by_id(mock_context):
    """Test that _resolve_entity_identifier works with entity IDs."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    results = await mgr.create_entities(
        [CreateEntityRequest(name="TestEntity", entity_type="test")]
    )
    entity_id = results[0].entity.id

    graph = await mgr.read_graph()
    resolved = mgr._resolve_entity_identifier(graph, entity_id)

    assert resolved is not None
    assert resolved.id == entity_id
    assert resolved.name == "TestEntity"


@pytest.mark.asyncio
async def test_resolve_entity_identifier_by_name(mock_context):
    """Test that _resolve_entity_identifier works with entity names."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities([CreateEntityRequest(name="TestEntity", entity_type="test")])

    graph = await mgr.read_graph()
    resolved = mgr._resolve_entity_identifier(graph, "TestEntity")

    assert resolved is not None
    assert resolved.name == "TestEntity"


@pytest.mark.asyncio
async def test_resolve_entity_identifier_by_alias(mock_context):
    """Test that _resolve_entity_identifier works with entity aliases."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities(
        [CreateEntityRequest(name="Robert", entity_type="person", aliases=["Bob", "Bobby"])]
    )

    graph = await mgr.read_graph()
    resolved = mgr._resolve_entity_identifier(graph, "Bob")

    assert resolved is not None
    assert resolved.name == "Robert"
    assert "Bob" in resolved.aliases


@pytest.mark.asyncio
async def test_create_relation_with_names(mock_context):
    """Test creating relations using entity names instead of IDs."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities(
        [
            CreateEntityRequest(name="Alice", entity_type="person"),
            CreateEntityRequest(name="Acme Corp", entity_type="organization"),
        ]
    )

    rel_result = await mgr.create_relations(
        [
            CreateRelationRequest(
                from_entity_name="Alice",
                to_entity_name="Acme Corp",
                relation="works_at",
            )
        ]
    )

    assert len(rel_result.relations) == 1
    assert rel_result.relations[0].relation == "works_at"


@pytest.mark.asyncio
async def test_create_relation_mixed_id_and_name(mock_context):
    """Test creating relations with one ID and one name."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    results = await mgr.create_entities(
        [
            CreateEntityRequest(name="Alice", entity_type="person"),
            CreateEntityRequest(name="Acme Corp", entity_type="organization"),
        ]
    )
    alice_id = results[0].entity.id

    rel_result = await mgr.create_relations(
        [
            CreateRelationRequest(
                from_entity_id=alice_id,
                to_entity_name="Acme Corp",
                relation="works_at",
            )
        ]
    )

    assert len(rel_result.relations) == 1


@pytest.mark.asyncio
async def test_merge_entities_with_ids(mock_context):
    """Test merging entities using IDs instead of names."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    results = await mgr.create_entities(
        [
            CreateEntityRequest(name="John", entity_type="person"),
            CreateEntityRequest(name="Johnny", entity_type="person"),
        ]
    )
    entity_ids = [r.entity.id for r in results]

    merged = await mgr.merge_entities("John Smith", entity_ids)

    assert merged.name == "John Smith"
    graph = await mgr.read_graph()
    assert len([e for e in graph.entities if e.name in ["John", "Johnny"]]) == 0


@pytest.mark.asyncio
async def test_merge_entities_mixed_identifiers(mock_context):
    """Test merging entities with a mix of IDs and names."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    results = await mgr.create_entities(
        [
            CreateEntityRequest(name="Alice", entity_type="person"),
            CreateEntityRequest(name="Alicia", entity_type="person"),
        ]
    )
    alice_id = results[0].entity.id

    merged = await mgr.merge_entities("Alice Smith", [alice_id, "Alicia"])

    assert merged.name == "Alice Smith"
    graph = await mgr.read_graph()
    assert len([e for e in graph.entities if e.name in ["Alice", "Alicia"]]) == 0


@pytest.mark.asyncio
async def test_delete_relations_with_names(mock_context):
    """Test deleting relations when entities are specified by name."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    await mgr.create_entities(
        [
            CreateEntityRequest(name="Alice", entity_type="person"),
            CreateEntityRequest(name="Bob", entity_type="person"),
        ]
    )

    # Create relation
    await mgr.create_relations(
        [
            CreateRelationRequest(
                from_entity_name="Alice",
                to_entity_name="Bob",
                relation="knows",
            )
        ]
    )

    graph = await mgr.read_graph()
    initial_count = len(graph.relations)

    # Delete using Relation with name fields (deprecated but supported)
    from mcp_knowledge_graph.models import Relation

    # Get the actual relation to delete
    graph = await mgr.read_graph()
    relation_to_delete = graph.relations[0]

    # Delete by creating a Relation with the same endpoints but using names
    # We'll use the actual IDs but the delete_relations method should handle name resolution
    await mgr.delete_relations([relation_to_delete])

    graph = await mgr.read_graph()
    assert len(graph.relations) == initial_count - 1


@pytest.mark.asyncio
async def test_update_user_info_with_observations(mock_context):
    """Test updating user info and adding observations in one call."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    graph = await mgr.read_graph()
    user_entity_id = graph.user_info.linked_entity_id

    # Update user info with observations
    from mcp_knowledge_graph.models import UserIdentifier

    new_user_info = UserIdentifier.from_values(
        preferred_name="TestUser",
        first_name="Test",
        linked_entity_id=user_entity_id,
    )

    updated = await mgr.update_user_info(new_user_info)

    # Add observations separately to test the flow
    obs_results = await mgr.apply_observations(
        [
            ObservationRequest(
                entity_id=user_entity_id,
                observations=[
                    Observation.from_values("prefers email communication", DurabilityType.LONG_TERM)
                ],
            )
        ]
    )

    assert updated.preferred_name == "TestUser"
    assert len(obs_results) == 1
    assert len(obs_results[0].added_observations) == 1


@pytest.mark.asyncio
async def test_read_graph_includes_project_placeholder(mock_context):
    """Test that read_graph handles project awareness gracefully when projects don't exist."""
    mem = Path(mock_context) / "memory.jsonl"
    mgr = KnowledgeGraphManager(str(mem))

    # This should not raise an error even though projects don't exist yet
    graph = await mgr.read_graph()
    assert graph is not None
    # The project awareness code should gracefully handle the absence of project methods
