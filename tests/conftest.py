"""
Pytest configuration and fixtures for IQ-MCP tests.

This module provides shared fixtures for setting up isolated test environments
and mocking dependencies for reliable, repeatable testing.
"""

import os
import tempfile
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Generator
import pytest

try:
    import pytest_asyncio
except ImportError:
    pytest_asyncio = None

from src.mcp_knowledge_graph.manager import KnowledgeGraphManager
from src.mcp_knowledge_graph.models import (
    Entity,
    Relation,
    TimestampedObservation,
    DurabilityType,
    ObservationInput,
    AddObservationRequest,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    
    yield loop
    
    # Clean up
    try:
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()
    except Exception:
        pass


@pytest_asyncio.fixture
async def temp_memory_file() -> AsyncGenerator[str, None]:
    """
    Create a temporary memory file for testing.
    
    Yields:
        Path to a temporary JSONL file that will be cleaned up after the test
    """
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
        temp_path = f.name
    
    try:
        yield temp_path
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_path):
            os.unlink(temp_path)


@pytest_asyncio.fixture
async def manager(temp_memory_file: str) -> AsyncGenerator[KnowledgeGraphManager, None]:
    """
    Create a KnowledgeGraphManager instance with a temporary memory file.
    
    Args:
        temp_memory_file: Path to temporary memory file from fixture
        
    Yields:
        KnowledgeGraphManager instance for testing
    """
    # Create manager with temporary file
    mgr = KnowledgeGraphManager(temp_memory_file)
    yield mgr


@pytest_asyncio.fixture
async def sample_entities() -> list[Entity]:
    """
    Create sample entities for testing.
    
    Returns:
        List of sample Entity objects with varied entity types and observations
    """
    return [
        Entity(
            name="Alice Johnson",
            entity_type="person",
            observations=[
                "Software engineer at TechCorp",
                "Lives in San Francisco",
                "Enjoys hiking and photography"
            ]
        ),
        Entity(
            name="TechCorp",
            entity_type="organization",
            observations=[
                "Technology company founded in 2010",
                "Specializes in cloud computing",
                "Has 500+ employees"
            ]
        ),
        Entity(
            name="Project Alpha",
            entity_type="project",
            observations=[
                "Machine learning initiative",
                "Started in Q2 2023",
                "Budget of $2M"
            ]
        )
    ]


@pytest_asyncio.fixture
async def sample_relations() -> list[Relation]:
    """
    Create sample relations for testing.
    
    Returns:
        List of sample Relation objects representing various relationship types
    """
    return [
        Relation(
            from_entity="Alice Johnson",
            to_entity="TechCorp",
            relation_type="works at"
        ),
        Relation(
            from_entity="Alice Johnson",
            to_entity="Project Alpha",
            relation_type="leads"
        ),
        Relation(
            from_entity="TechCorp",
            to_entity="Project Alpha",
            relation_type="sponsors"
        )
    ]


@pytest_asyncio.fixture
async def sample_observation_requests() -> list[AddObservationRequest]:
    """
    Create sample observation requests for testing.
    
    Returns:
        List of AddObservationRequest objects with mixed content types
    """
    return [
        AddObservationRequest(
            entity_name="Alice Johnson",
            contents=[
                "Completed Python certification",
                ObservationInput(
                    content="Currently learning TypeScript",
                    durability=DurabilityType.TEMPORARY
                )
            ]
        ),
        AddObservationRequest(
            entity_name="TechCorp",
            contents=[
                ObservationInput(
                    content="Founded by John Doe",
                    durability=DurabilityType.PERMANENT
                ),
                "Acquired StartupX in 2023"
            ]
        )
    ]


@pytest_asyncio.fixture
async def populated_manager(
    manager: KnowledgeGraphManager,
    sample_entities: list[Entity],
    sample_relations: list[Relation]
) -> AsyncGenerator[KnowledgeGraphManager, None]:
    """
    Create a manager with pre-populated sample data.
    
    Args:
        manager: Empty KnowledgeGraphManager from fixture
        sample_entities: Sample entities to populate
        sample_relations: Sample relations to populate
        
    Yields:
        KnowledgeGraphManager with sample data already loaded
    """
    # Populate with sample data
    await manager.create_entities(sample_entities)
    await manager.create_relations(sample_relations)
    
    yield manager


@pytest.fixture
def mock_env_memory_path(temp_memory_file: str, monkeypatch: pytest.MonkeyPatch) -> str:
    """
    Mock the MEMORY_FILE_PATH environment variable.
    
    Args:
        temp_memory_file: Temporary file path from fixture
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        The temporary file path that was set in the environment
    """
    monkeypatch.setenv("MEMORY_FILE_PATH", temp_memory_file)
    return temp_memory_file