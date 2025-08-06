"""
Integration tests for the IQ-MCP Knowledge Graph Server.

This module tests complete workflows and integration between different
components of the knowledge graph system.
"""

import json
import pytest
import pytest_asyncio
from typing import Any, Dict, List

from src.mcp_knowledge_graph.server import (
    create_entities,
    create_relations,
    add_observations,
    delete_entities,
    read_graph,
    search_nodes,
    open_nodes,
)


class TestCompleteWorkflows:
    """Test complete workflows combining multiple operations."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_manager(self, temp_memory_file: str, monkeypatch: pytest.MonkeyPatch):
        """Setup a fresh manager for each test."""
        from src.mcp_knowledge_graph import server
        test_manager = server.KnowledgeGraphManager(temp_memory_file)
        monkeypatch.setattr(server, "manager", test_manager)
    
    async def test_create_team_and_project_workflow(self):
        """Test a complete workflow of creating a team, project, and relationships."""
        
        # Step 1: Create team members
        team_entities = [
            {
                "name": "Sarah Chen",
                "entityType": "person",
                "observations": [
                    "Senior Software Engineer",
                    "Python specialist",
                    "5 years experience"
                ]
            },
            {
                "name": "Mike Rodriguez",
                "entityType": "person", 
                "observations": [
                    "Product Manager",
                    "Agile expert",
                    "Former startup founder"
                ]
            },
            {
                "name": "TechStart Inc",
                "entityType": "organization",
                "observations": [
                    "AI startup",
                    "Founded in 2022",
                    "Series A funded"
                ]
            }
        ]
        
        entities_result = await create_entities(team_entities)
        assert len(entities_result) == 3
        
        # Step 2: Create project
        project_entities = [
            {
                "name": "AI Chat Platform",
                "entityType": "project",
                "observations": [
                    "Customer service chatbot",
                    "Uses GPT-4",
                    "6 month timeline"
                ]
            }
        ]
        
        project_result = await create_entities(project_entities)
        assert len(project_result) == 1
        
        # Step 3: Create relationships
        relationships = [
            {"from": "Sarah Chen", "to": "TechStart Inc", "relationType": "works at"},
            {"from": "Mike Rodriguez", "to": "TechStart Inc", "relationType": "works at"},
            {"from": "TechStart Inc", "to": "AI Chat Platform", "relationType": "sponsors"},
            {"from": "Sarah Chen", "to": "AI Chat Platform", "relationType": "develops"},
            {"from": "Mike Rodriguez", "to": "AI Chat Platform", "relationType": "manages"}
        ]
        
        relations_result = await create_relations(relationships)
        assert len(relations_result) == 5
        
        # Step 4: Add temporal observations
        observations_data = [
            {
                "entityName": "AI Chat Platform",
                "contents": [
                    {"content": "Project started", "durability": "permanent"},
                    {"content": "Currently in development phase", "durability": "short-term"},
                    {"content": "Weekly team meetings on Fridays", "durability": "temporary"}
                ]
            }
        ]
        
        obs_result = await add_observations(observations_data)
        assert len(obs_result[0]["added_observations"]) == 3
        
        # Step 5: Verify complete graph
        graph = await read_graph()
        assert len(graph["entities"]) == 4  # 3 team + 1 project
        assert len(graph["relations"]) == 5
        
        # Step 6: Test search functionality
        search_result = await search_nodes("Sarah")
        sarah_found = any(e["name"] == "Sarah Chen" for e in search_result["entities"])
        assert sarah_found
        
        # Step 7: Test opening specific nodes
        team_nodes = await open_nodes(["Sarah Chen", "Mike Rodriguez"])
        assert len(team_nodes["entities"]) == 2
    
    async def test_company_acquisition_workflow(self):
        """Test workflow for modeling a company acquisition."""
        
        # Create companies
        companies = [
            {
                "name": "BigCorp Industries",
                "entityType": "organization",
                "observations": [
                    "Fortune 500 company",
                    "Technology conglomerate",
                    "Founded in 1985"
                ]
            },
            {
                "name": "InnovateTech",
                "entityType": "organization",
                "observations": [
                    "AI startup",
                    "Founded in 2020",
                    "Valued at $50M"
                ]
            }
        ]
        
        await create_entities(companies)
        
        # Model the acquisition
        acquisition_relations = [
            {"from": "BigCorp Industries", "to": "InnovateTech", "relationType": "acquires"}
        ]
        
        await create_relations(acquisition_relations)
        
        # Add temporal observations about the acquisition
        acquisition_obs = [
            {
                "entityName": "BigCorp Industries",
                "contents": [
                    {"content": "Announced acquisition of InnovateTech", "durability": "permanent"},
                    {"content": "Acquisition pending regulatory approval", "durability": "temporary"}
                ]
            },
            {
                "entityName": "InnovateTech", 
                "contents": [
                    {"content": "Being acquired by BigCorp", "durability": "permanent"},
                    {"content": "Integration planning in progress", "durability": "short-term"}
                ]
            }
        ]
        
        await add_observations(acquisition_obs)
        
        # Verify the acquisition is properly modeled
        graph = await read_graph()
        
        # Find the acquisition relation
        acquisition_rel = next(
            (r for r in graph["relations"] 
             if r["from"] == "BigCorp Industries" and r["relationType"] == "acquires"),
            None
        )
        assert acquisition_rel is not None
        assert acquisition_rel["to"] == "InnovateTech"
        
        # Search for acquisition-related entities
        search_result = await search_nodes("acquisition")
        assert len(search_result["entities"]) >= 1
    
    async def test_data_persistence_across_operations(self):
        """Test that data persists correctly across multiple operations."""
        
        # Create initial data
        initial_entities = [
            {"name": "Persistence Test", "entityType": "person", "observations": ["Initial observation"]}
        ]
        await create_entities(initial_entities)
        
        # Add more observations
        additional_obs = [
            {
                "entityName": "Persistence Test",
                "contents": ["Additional observation"]
            }
        ]
        await add_observations(additional_obs)
        
        # Create another entity and relate it
        related_entities = [
            {"name": "Related Entity", "entityType": "organization", "observations": []}
        ]
        await create_entities(related_entities)
        
        relations = [
            {"from": "Persistence Test", "to": "Related Entity", "relationType": "affiliated with"}
        ]
        await create_relations(relations)
        
        # Verify all data persists
        graph = await read_graph()
        
        # Check entities
        persistence_entity = next(
            (e for e in graph["entities"] if e["name"] == "Persistence Test"),
            None
        )
        assert persistence_entity is not None
        
        # Check observations count (should have both initial and additional)
        obs_count = len(persistence_entity["observations"])
        assert obs_count == 2
        
        # Check relations
        relation = next(
            (r for r in graph["relations"] 
             if r["from"] == "Persistence Test" and r["to"] == "Related Entity"),
            None
        )
        assert relation is not None
    
    async def test_entity_deletion_cascades_relations(self):
        """Test that deleting entities also removes related relations."""
        
        # Create entities and relations
        entities = [
            {"name": "Entity A", "entityType": "person", "observations": []},
            {"name": "Entity B", "entityType": "person", "observations": []},
            {"name": "Entity C", "entityType": "person", "observations": []}
        ]
        await create_entities(entities)
        
        relations = [
            {"from": "Entity A", "to": "Entity B", "relationType": "knows"},
            {"from": "Entity B", "to": "Entity C", "relationType": "manages"},
            {"from": "Entity A", "to": "Entity C", "relationType": "collaborates with"}
        ]
        await create_relations(relations)
        
        # Verify initial state
        initial_graph = await read_graph()
        assert len(initial_graph["entities"]) == 3
        assert len(initial_graph["relations"]) == 3
        
        # Delete Entity B
        await delete_entities(["Entity B"])
        
        # Verify Entity B and its relations are gone
        final_graph = await read_graph()
        
        # Entity B should be gone
        entity_names = [e["name"] for e in final_graph["entities"]]
        assert "Entity B" not in entity_names
        assert "Entity A" in entity_names
        assert "Entity C" in entity_names
        
        # Relations involving Entity B should be gone
        remaining_relations = final_graph["relations"]
        entity_b_relations = [
            r for r in remaining_relations 
            if r["from"] == "Entity B" or r["to"] == "Entity B"
        ]
        assert len(entity_b_relations) == 0
        
        # Relation between A and C should remain
        a_to_c_relation = next(
            (r for r in remaining_relations 
             if r["from"] == "Entity A" and r["to"] == "Entity C"),
            None
        )
        assert a_to_c_relation is not None


class TestConcurrentOperations:
    """Test handling of concurrent operations on the knowledge graph."""
    
    @pytest_asyncio.fixture(autouse=True)
    async def setup_test_manager(self, temp_memory_file: str, monkeypatch: pytest.MonkeyPatch):
        """Setup a fresh manager for each test."""
        from src.mcp_knowledge_graph import server
        test_manager = server.KnowledgeGraphManager(temp_memory_file)
        monkeypatch.setattr(server, "manager", test_manager)
    
    async def test_multiple_entity_operations(self):
        """Test multiple entity operations in sequence."""
        
        # Create multiple batches of entities
        batch1 = [
            {"name": "Batch1 Entity1", "entityType": "person", "observations": []},
            {"name": "Batch1 Entity2", "entityType": "person", "observations": []}
        ]
        
        batch2 = [
            {"name": "Batch2 Entity1", "entityType": "organization", "observations": []},
            {"name": "Batch2 Entity2", "entityType": "organization", "observations": []}
        ]
        
        # Create batches
        result1 = await create_entities(batch1)
        result2 = await create_entities(batch2)
        
        assert len(result1) == 2
        assert len(result2) == 2
        
        # Verify all entities exist
        graph = await read_graph()
        assert len(graph["entities"]) == 4
        
        entity_names = [e["name"] for e in graph["entities"]]
        assert "Batch1 Entity1" in entity_names
        assert "Batch1 Entity2" in entity_names  
        assert "Batch2 Entity1" in entity_names
        assert "Batch2 Entity2" in entity_names
    
    async def test_mixed_operation_sequence(self):
        """Test a sequence of mixed operations (create, read, update, delete)."""
        
        # 1. Create initial entities
        entities = [
            {"name": "Mixed Op Test", "entityType": "person", "observations": ["Initial"]}
        ]
        create_result = await create_entities(entities)
        assert len(create_result) == 1
        
        # 2. Read current state
        graph1 = await read_graph()
        assert len(graph1["entities"]) == 1
        
        # 3. Add observations (update)
        observations = [
            {
                "entityName": "Mixed Op Test",
                "contents": ["Updated observation"]
            }
        ]
        obs_result = await add_observations(observations)
        assert len(obs_result[0]["added_observations"]) == 1
        
        # 4. Read updated state
        graph2 = await read_graph()
        entity = graph2["entities"][0]
        assert len(entity["observations"]) == 2
        
        # 5. Search for entity
        search_result = await search_nodes("Mixed Op Test")
        assert len(search_result["entities"]) == 1
        
        # 6. Delete entity
        await delete_entities(["Mixed Op Test"])
        
        # 7. Verify deletion
        final_graph = await read_graph()
        assert len(final_graph["entities"]) == 0