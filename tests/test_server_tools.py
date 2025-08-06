"""
Tests for the MCP server tool functions.

This module comprehensively tests all CRUD operations exposed by the FastMCP server,
including entity management, relations, observations, and graph operations.
"""

import json
import pytest
import pytest_asyncio
from typing import Any, Dict, List

from src.mcp_knowledge_graph.server import (
    create_entities,
    create_relations,
    add_observations,
    cleanup_outdated_observations,
    get_observations_by_durability,
    delete_entities,
    delete_observations,
    delete_relations,
    read_graph,
    search_nodes,
    open_nodes,
    manager,
)
from src.mcp_knowledge_graph.models import (
    Entity,
    Relation,
    DurabilityType,
    ObservationInput,
    AddObservationRequest,
    DeleteObservationRequest,
)


class TestEntityCRUD:
    """Test suite for entity CRUD operations."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_manager(self, temp_memory_file: str, monkeypatch: pytest.MonkeyPatch):
        """Setup a fresh manager for each test."""
        # Replace the global manager with one using temp file
        from src.mcp_knowledge_graph import server
        test_manager = server.KnowledgeGraphManager(temp_memory_file)
        monkeypatch.setattr(server, "manager", test_manager)
    
    async def test_create_entities_list_input(self):
        """Test creating entities with list input."""
        entities_data = [
            {
                "name": "John Doe",
                "entityType": "person",
                "observations": ["Software developer", "Lives in NYC"]
            },
            {
                "name": "Acme Corp",
                "entityType": "organization", 
                "observations": ["Technology company", "Founded in 2020"]
            }
        ]
        
        result = await create_entities(entities_data)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "John Doe"
        assert result[0]["entityType"] == "person"
        assert result[1]["name"] == "Acme Corp"
        assert result[1]["entityType"] == "organization"
    
    async def test_create_entities_json_string_input(self):
        """Test creating entities with JSON string input."""
        entities_data = [
            {
                "name": "Jane Smith",
                "entityType": "person",
                "observations": ["Data scientist", "PhD in Statistics"]
            }
        ]
        json_string = json.dumps(entities_data)
        
        result = await create_entities(json_string)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "Jane Smith"
    
    async def test_create_entities_duplicate_prevention(self):
        """Test that duplicate entities are not created."""
        entities_data = [
            {
                "name": "Duplicate Test",
                "entityType": "person", 
                "observations": ["First version"]
            }
        ]
        
        # Create first time
        result1 = await create_entities(entities_data)
        assert len(result1) == 1
        
        # Try to create again
        result2 = await create_entities(entities_data)
        assert len(result2) == 0  # No new entities created
    
    async def test_delete_entities_list_input(self):
        """Test deleting entities with list input."""
        # First create entities
        entities_data = [
            {"name": "Delete Me 1", "entityType": "person", "observations": []},
            {"name": "Delete Me 2", "entityType": "person", "observations": []}
        ]
        await create_entities(entities_data)
        
        # Delete them
        result = await delete_entities(["Delete Me 1", "Delete Me 2"])
        assert result == "Entities deleted successfully"
        
        # Verify they're gone
        graph = await read_graph()
        entity_names = [e["name"] for e in graph["entities"]]
        assert "Delete Me 1" not in entity_names
        assert "Delete Me 2" not in entity_names
    
    async def test_delete_entities_json_string_input(self):
        """Test deleting entities with JSON string input."""
        # First create entity
        entities_data = [{"name": "Delete JSON Test", "entityType": "person", "observations": []}]
        await create_entities(entities_data)
        
        # Delete with JSON string
        result = await delete_entities(json.dumps(["Delete JSON Test"]))
        assert result == "Entities deleted successfully"
    
    async def test_open_nodes_list_input(self):
        """Test opening nodes with list input."""
        # First create entities
        entities_data = [
            {"name": "Open Test 1", "entityType": "person", "observations": ["Test observation"]},
            {"name": "Open Test 2", "entityType": "organization", "observations": ["Org observation"]}
        ]
        await create_entities(entities_data)
        
        # Open them
        result = await open_nodes(["Open Test 1", "Open Test 2"])
        
        assert "entities" in result
        assert len(result["entities"]) == 2
        
        names = [e["name"] for e in result["entities"]]
        assert "Open Test 1" in names
        assert "Open Test 2" in names
    
    async def test_open_nodes_json_string_input(self):
        """Test opening nodes with JSON string input."""
        # First create entity
        entities_data = [{"name": "Open JSON Test", "entityType": "person", "observations": ["Test"]}]
        await create_entities(entities_data)
        
        # Open with JSON string
        result = await open_nodes(json.dumps(["Open JSON Test"]))
        
        assert "entities" in result
        assert len(result["entities"]) == 1
        assert result["entities"][0]["name"] == "Open JSON Test"


class TestRelationCRUD:
    """Test suite for relation CRUD operations."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_manager(self, temp_memory_file: str, monkeypatch: pytest.MonkeyPatch):
        """Setup a fresh manager for each test."""
        from src.mcp_knowledge_graph import server
        test_manager = server.KnowledgeGraphManager(temp_memory_file)
        monkeypatch.setattr(server, "manager", test_manager)
    
    async def test_create_relations_list_input(self):
        """Test creating relations with list input."""
        # First create entities
        entities_data = [
            {"name": "Person A", "entityType": "person", "observations": []},
            {"name": "Company B", "entityType": "organization", "observations": []}
        ]
        await create_entities(entities_data)
        
        # Create relations
        relations_data = [
            {"from": "Person A", "to": "Company B", "relationType": "works at"},
            {"from": "Company B", "to": "Person A", "relationType": "employs"}
        ]
        
        result = await create_relations(relations_data)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["from"] == "Person A"
        assert result[0]["relationType"] == "works at"
    
    async def test_create_relations_json_string_input(self):
        """Test creating relations with JSON string input."""
        # First create entities
        entities_data = [
            {"name": "JSON Person", "entityType": "person", "observations": []},
            {"name": "JSON Company", "entityType": "organization", "observations": []}
        ]
        await create_entities(entities_data)
        
        # Create relations with JSON string
        relations_data = [{"from": "JSON Person", "to": "JSON Company", "relationType": "collaborates with"}]
        json_string = json.dumps(relations_data)
        
        result = await create_relations(json_string)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["relationType"] == "collaborates with"
    
    async def test_create_relations_duplicate_prevention(self):
        """Test that duplicate relations are not created."""
        # First create entities
        entities_data = [
            {"name": "Dup Person", "entityType": "person", "observations": []},
            {"name": "Dup Company", "entityType": "organization", "observations": []}
        ]
        await create_entities(entities_data)
        
        relations_data = [{"from": "Dup Person", "to": "Dup Company", "relationType": "works at"}]
        
        # Create first time
        result1 = await create_relations(relations_data)
        assert len(result1) == 1
        
        # Try to create again
        result2 = await create_relations(relations_data)
        assert len(result2) == 0  # No new relations created
    
    async def test_delete_relations_list_input(self):
        """Test deleting relations with list input."""
        # Setup entities and relations
        entities_data = [
            {"name": "Del Person", "entityType": "person", "observations": []},
            {"name": "Del Company", "entityType": "organization", "observations": []}
        ]
        await create_entities(entities_data)
        
        relations_data = [{"from": "Del Person", "to": "Del Company", "relationType": "works at"}]
        await create_relations(relations_data)
        
        # Delete relations
        result = await delete_relations(relations_data)
        assert result == "Relations deleted successfully"
        
        # Verify they're gone
        graph = await read_graph()
        assert len(graph["relations"]) == 0
    
    async def test_delete_relations_json_string_input(self):
        """Test deleting relations with JSON string input."""
        # Setup entities and relations
        entities_data = [
            {"name": "JSON Del Person", "entityType": "person", "observations": []},
            {"name": "JSON Del Company", "entityType": "organization", "observations": []}
        ]
        await create_entities(entities_data)
        
        relations_data = [{"from": "JSON Del Person", "to": "JSON Del Company", "relationType": "manages"}]
        await create_relations(relations_data)
        
        # Delete with JSON string
        result = await delete_relations(json.dumps(relations_data))
        assert result == "Relations deleted successfully"


class TestObservationCRUD:
    """Test suite for observation CRUD operations."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_manager(self, temp_memory_file: str, monkeypatch: pytest.MonkeyPatch):
        """Setup a fresh manager for each test."""
        from src.mcp_knowledge_graph import server
        test_manager = server.KnowledgeGraphManager(temp_memory_file)
        monkeypatch.setattr(server, "manager", test_manager)
    
    async def test_add_observations_list_input(self):
        """Test adding observations with list input."""
        # First create entity
        entities_data = [{"name": "Obs Test Person", "entityType": "person", "observations": []}]
        await create_entities(entities_data)
        
        # Add observations
        observations_data = [
            {
                "entityName": "Obs Test Person",
                "contents": [
                    "Simple string observation",
                    {"content": "Temporal observation", "durability": "temporary"}
                ]
            }
        ]
        
        result = await add_observations(observations_data)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["entity_name"] == "Obs Test Person"
        assert len(result[0]["added_observations"]) == 2
    
    async def test_add_observations_json_string_input(self):
        """Test adding observations with JSON string input."""
        # First create entity
        entities_data = [{"name": "JSON Obs Person", "entityType": "person", "observations": []}]
        await create_entities(entities_data)
        
        # Add observations with JSON string
        observations_data = [
            {
                "entityName": "JSON Obs Person",
                "contents": ["JSON observation test"]
            }
        ]
        json_string = json.dumps(observations_data)
        
        result = await add_observations(json_string)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert len(result[0]["added_observations"]) == 1
    
    async def test_add_observations_duplicate_prevention(self):
        """Test that duplicate observations are not added."""
        # First create entity
        entities_data = [{"name": "Dup Obs Person", "entityType": "person", "observations": ["Existing observation"]}]
        await create_entities(entities_data)
        
        # Try to add the same observation
        observations_data = [
            {
                "entityName": "Dup Obs Person",
                "contents": ["Existing observation"]
            }
        ]
        
        result = await add_observations(observations_data)
        
        # Should not add duplicates
        assert len(result[0]["added_observations"]) == 0
    
    async def test_get_observations_by_durability(self):
        """Test getting observations grouped by durability."""
        # First create entity and add varied observations
        entities_data = [{"name": "Durability Test", "entityType": "person", "observations": []}]
        await create_entities(entities_data)
        
        observations_data = [
            {
                "entityName": "Durability Test",
                "contents": [
                    {"content": "Permanent fact", "durability": "permanent"},
                    {"content": "Long term info", "durability": "long-term"},
                    {"content": "Short term note", "durability": "short-term"},
                    {"content": "Temporary data", "durability": "temporary"}
                ]
            }
        ]
        await add_observations(observations_data)
        
        # Get observations by durability
        result = await get_observations_by_durability("Durability Test")
        
        assert "permanent" in result
        assert "long_term" in result
        assert "short_term" in result
        assert "temporary" in result
        
        assert len(result["permanent"]) == 1
        assert len(result["long_term"]) == 1
        assert len(result["short_term"]) == 1
        assert len(result["temporary"]) == 1
    
    async def test_delete_observations_list_input(self):
        """Test deleting observations with list input."""
        # Setup entity with observations
        entities_data = [{"name": "Del Obs Person", "entityType": "person", "observations": ["Keep this", "Delete this"]}]
        await create_entities(entities_data)
        
        # Delete specific observation
        deletions_data = [
            {
                "entityName": "Del Obs Person",
                "observations": ["Delete this"]
            }
        ]
        
        result = await delete_observations(deletions_data)
        assert result == "Observations deleted successfully"
        
        # Verify only the right observation was deleted
        graph = await read_graph()
        entity = next(e for e in graph["entities"] if e["name"] == "Del Obs Person")
        obs_contents = [obs["content"] if isinstance(obs, dict) else obs for obs in entity["observations"]]
        assert "Keep this" in obs_contents
        assert "Delete this" not in obs_contents
    
    async def test_delete_observations_json_string_input(self):
        """Test deleting observations with JSON string input."""
        # Setup entity with observations
        entities_data = [{"name": "JSON Del Obs", "entityType": "person", "observations": ["JSON observation"]}]
        await create_entities(entities_data)
        
        # Delete with JSON string
        deletions_data = [{"entityName": "JSON Del Obs", "observations": ["JSON observation"]}]
        json_string = json.dumps(deletions_data)
        
        result = await delete_observations(json_string)
        assert result == "Observations deleted successfully"


class TestGraphOperations:
    """Test suite for graph-level operations."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_manager(self, temp_memory_file: str, monkeypatch: pytest.MonkeyPatch):
        """Setup a fresh manager for each test."""
        from src.mcp_knowledge_graph import server
        test_manager = server.KnowledgeGraphManager(temp_memory_file)
        monkeypatch.setattr(server, "manager", test_manager)
    
    async def test_read_graph_empty(self):
        """Test reading an empty graph."""
        result = await read_graph()
        
        assert "entities" in result
        assert "relations" in result
        assert len(result["entities"]) == 0
        assert len(result["relations"]) == 0
    
    async def test_read_graph_populated(self):
        """Test reading a populated graph."""
        # Add some data
        entities_data = [{"name": "Read Test", "entityType": "person", "observations": ["Test"]}]
        await create_entities(entities_data)
        
        result = await read_graph()
        
        assert len(result["entities"]) == 1
        assert result["entities"][0]["name"] == "Read Test"
    
    async def test_search_nodes_by_name(self):
        """Test searching nodes by entity name."""
        # Add test data
        entities_data = [
            {"name": "Searchable Person", "entityType": "person", "observations": ["Software engineer"]},
            {"name": "Another Entity", "entityType": "organization", "observations": ["Company"]}
        ]
        await create_entities(entities_data)
        
        # Search for specific name
        result = await search_nodes("Searchable")
        
        assert "entities" in result
        assert len(result["entities"]) >= 1
        
        # Should find the entity with "Searchable" in the name
        names = [e["name"] for e in result["entities"]]
        assert any("Searchable" in name for name in names)
    
    async def test_search_nodes_by_observation(self):
        """Test searching nodes by observation content."""
        # Add test data
        entities_data = [
            {"name": "Engineer Person", "entityType": "person", "observations": ["Python developer", "Machine learning expert"]},
            {"name": "Designer Person", "entityType": "person", "observations": ["UI/UX designer", "Creative professional"]}
        ]
        await create_entities(entities_data)
        
        # Search by observation content
        result = await search_nodes("Python")
        
        assert "entities" in result
        # Should find entities with "Python" in observations
        found_engineer = any(e["name"] == "Engineer Person" for e in result["entities"])
        assert found_engineer
    
    async def test_search_nodes_by_entity_type(self):
        """Test searching nodes by entity type."""
        # Add test data
        entities_data = [
            {"name": "Test Person", "entityType": "person", "observations": []},
            {"name": "Test Organization", "entityType": "organization", "observations": []}
        ]
        await create_entities(entities_data)
        
        # Search by entity type
        result = await search_nodes("person")
        
        assert "entities" in result
        # Should find person entities
        person_entities = [e for e in result["entities"] if e["entityType"] == "person"]
        assert len(person_entities) >= 1
    
    async def test_cleanup_outdated_observations(self):
        """Test cleanup of outdated observations."""
        # This test is challenging because it depends on timestamps
        # We'll test that the function runs without error
        result = await cleanup_outdated_observations()
        
        assert "entities_processed" in result
        assert "observations_removed" in result
        assert "removed_observations" in result
        assert isinstance(result["entities_processed"], int)
        assert isinstance(result["observations_removed"], int)
        assert isinstance(result["removed_observations"], list)


class TestErrorHandling:
    """Test suite for error conditions and edge cases."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_manager(self, temp_memory_file: str, monkeypatch: pytest.MonkeyPatch):
        """Setup a fresh manager for each test."""
        from src.mcp_knowledge_graph import server
        test_manager = server.KnowledgeGraphManager(temp_memory_file)
        monkeypatch.setattr(server, "manager", test_manager)
    
    async def test_create_entities_invalid_json(self):
        """Test error handling for invalid JSON input."""
        with pytest.raises(RuntimeError, match="Failed to create entities"):
            await create_entities("invalid json string")
    
    async def test_create_entities_invalid_structure(self):
        """Test error handling for invalid entity structure."""
        with pytest.raises(RuntimeError, match="Failed to create entities"):
            await create_entities([{"name": "Test"}])  # Missing required fields
    
    async def test_add_observations_nonexistent_entity(self):
        """Test error handling when adding observations to non-existent entity."""
        observations_data = [
            {
                "entityName": "Nonexistent Entity",
                "contents": ["Some observation"]
            }
        ]
        
        with pytest.raises(RuntimeError, match="Failed to add observations"):
            await add_observations(observations_data)
    
    async def test_delete_entities_empty_list(self):
        """Test error handling for empty entity list."""
        with pytest.raises(RuntimeError, match="Failed to delete entities"):
            await delete_entities([])
    
    async def test_delete_entities_invalid_json(self):
        """Test error handling for invalid JSON in delete entities."""
        with pytest.raises(RuntimeError, match="Failed to delete entities"):
            await delete_entities("invalid json")
    
    async def test_open_nodes_empty_list(self):
        """Test error handling for empty node list."""
        with pytest.raises(RuntimeError, match="Failed to open nodes"):
            await open_nodes([])
    
    async def test_open_nodes_invalid_json(self):
        """Test error handling for invalid JSON in open nodes."""
        with pytest.raises(RuntimeError, match="Failed to open nodes"):
            await open_nodes("invalid json")
    
    async def test_get_observations_by_durability_empty_name(self):
        """Test error handling for empty entity name."""
        with pytest.raises(RuntimeError, match="Failed to get observations"):
            await get_observations_by_durability("")
    
    async def test_get_observations_by_durability_none_name(self):
        """Test error handling for None entity name."""
        with pytest.raises(RuntimeError, match="Failed to get observations"):
            await get_observations_by_durability(None)  # type: ignore
    
    async def test_search_nodes_empty_query(self):
        """Test error handling for empty search query."""
        with pytest.raises(RuntimeError, match="Failed to search nodes"):
            await search_nodes("")
    
    async def test_search_nodes_none_query(self):
        """Test error handling for None search query."""
        with pytest.raises(RuntimeError, match="Failed to search nodes"):
            await search_nodes(None)  # type: ignore


class TestInputValidation:
    """Test suite for input validation functions."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_manager(self, temp_memory_file: str, monkeypatch: pytest.MonkeyPatch):
        """Setup a fresh manager for each test."""
        from src.mcp_knowledge_graph import server
        test_manager = server.KnowledgeGraphManager(temp_memory_file)
        monkeypatch.setattr(server, "manager", test_manager)
    
    async def test_mixed_content_types_in_observations(self):
        """Test handling mixed content types in observation requests."""
        # Create entity first
        entities_data = [{"name": "Mixed Content Test", "entityType": "person", "observations": []}]
        await create_entities(entities_data)
        
        # Add mixed observation types
        observations_data = [
            {
                "entityName": "Mixed Content Test",
                "contents": [
                    "Simple string",
                    {"content": "Structured observation", "durability": "permanent"},
                    "Another string",
                    {"content": "Temporary note", "durability": "temporary"}
                ]
            }
        ]
        
        result = await add_observations(observations_data)
        
        # Should handle all content types properly
        assert len(result[0]["added_observations"]) == 4
        
        # Verify observations were added with correct durability
        durability_result = await get_observations_by_durability("Mixed Content Test")
        assert len(durability_result["permanent"]) == 1
        assert len(durability_result["temporary"]) == 1
        assert len(durability_result["long_term"]) == 2  # Default for strings