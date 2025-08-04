"""
FastMCP Server implementation for temporal knowledge graph memory.

This module implements the Model Context Protocol server that exposes
knowledge graph operations as tools for LLM integration using FastMCP 2.11.
"""

import argparse
import asyncio
import os
import sys
import logging

from pathlib import Path
from typing import Any, Dict, List

from fastmcp import FastMCP

from src.mcp_knowledge_graph.manager import KnowledgeGraphManager
from src.mcp_knowledge_graph.models import (
    Entity,
    Relation,
    AddObservationRequest,
    DeleteObservationRequest,
    ObservationInput,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("iq-mcp")
IQ_DEBUG = bool(os.getenv("IQ_DEBUG", "false").lower() == "true")
if IQ_DEBUG:
    logger.setLevel(logging.DEBUG)



# Memory path can be specified via environment variable
try:
    IQ_MEMORY_PATH = Path(os.getenv("IQ_MEMORY_PATH", "memory.jsonl"))
    logger.debug(f"Memory path: {IQ_MEMORY_PATH}")
except Exception as e:
    raise FileNotFoundError(f"Memory path error: {e}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Temporal-Enhanced MCP Knowledge Graph Server"
    )
    parser.add_argument(
        "--memory-path",
        type=str,
        help="Custom path for memory storage (overrides MEMORY_FILE_PATH env var)",
    )
    # Only parse args if running as main script
    if __name__ == "__main__":
        return parser.parse_args()
    else:
        # Return empty namespace when imported as module
        return argparse.Namespace(memory_path=None)


def get_memory_file_path() -> str:
    """
    Determine memory file path from CLI args, environment, or default.
    
    Priority: CLI args > environment variable > default
    """
    args = parse_args()
    
    # Default path relative to this module
    default_path = Path(__file__).parent.parent / "memory.json"
    
    if args.memory_path:
        # CLI argument provided
        memory_path = Path(args.memory_path)
        if memory_path.is_absolute():
            return str(memory_path)
        else:
            return str(Path(__file__).parent.parent / memory_path)
    
    elif os.getenv("MEMORY_FILE_PATH"):
        # Environment variable provided
        env_var = os.getenv("MEMORY_FILE_PATH")
        if env_var:  # Check for None to satisfy type checker
            env_path = Path(env_var)
            if env_path.is_absolute():
                return str(env_path)
            else:
                return str(Path(__file__).parent.parent / env_path)
    
    # Use default
    return str(default_path)


# Initialize the knowledge graph manager and FastMCP server
memory_path = get_memory_file_path()
manager = KnowledgeGraphManager(memory_path)

# Create FastMCP server instance
mcp = FastMCP("iq-mcp")


@mcp.tool
async def create_entities(entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Create multiple new entities in the knowledge graph.
    
    Args:
        entities: List of entity objects with name, entityType, and observations
    
    Returns:
        List of created entity objects
    """
    try:
        entity_objects = []
        for entity_data in entities:
            try:
                entity_objects.append(Entity(**entity_data))
            except Exception as e:
                raise ValueError(f"Invalid entity data: {e}")
        
        result = await manager.create_entities(entity_objects)
        logger.debug("🛠️ Tool registered: create_entities")
        return [e.dict() for e in result]
    except Exception as e:
        raise RuntimeError(f"Failed to create entities: {e}")


@mcp.tool
async def create_relations(relations: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Create multiple new relations between entities in the knowledge graph. Relations should be in active voice.
    
    Args:
        relations: List of relation objects with from, to, and relationType fields
    
    Returns:
        List of created relation objects
    """
    try:
        relation_objects = []
        for relation_data in relations:
            try:
                relation_objects.append(Relation(**relation_data))
            except Exception as e:
                raise ValueError(f"Invalid relation data: {e}")
        
        result = await manager.create_relations(relation_objects)
        logger.debug("🛠️ Tool registered: create_relations")
        return [r.dict() for r in result]
    except Exception as e:
        raise RuntimeError(f"Failed to create relations: {e}")


@mcp.tool
async def add_observations(observations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Add new observations to existing entities in the knowledge graph. Supports both simple strings and temporal observations with durability metadata (permanent, long-term, short-term, temporary).
    
    Args:
        observations: List of observation objects with entityName and contents (can be strings or objects with durability)
    
    Returns:
        List of processed observation request objects
    """
    try:
        requests = []
        for obs_data in observations:
            if "entityName" not in obs_data or "contents" not in obs_data:
                raise ValueError("Missing required fields: entityName and contents")
            
            # Handle mixed content types (strings and objects)
            contents = []
            for content in obs_data["contents"]:
                if isinstance(content, str):
                    contents.append(content)
                elif isinstance(content, dict):
                    try:
                        contents.append(ObservationInput(**content))
                    except Exception as e:
                        raise ValueError(f"Invalid observation content: {e}")
                else:
                    raise ValueError(f"Invalid content type: {type(content)}")
            
            requests.append(AddObservationRequest(
                entity_name=obs_data["entityName"],
                contents=contents
            ))
        
        result = await manager.add_observations(requests)
        logger.debug("🛠️ Tool registered: add_observations")
        return [r.model_dump() for r in result]
    except Exception as e:
        raise RuntimeError(f"Failed to add observations: {e}")


@mcp.tool
async def cleanup_outdated_observations() -> Dict[str, Any]:
    """Remove observations that are likely outdated based on their durability and age.
    
    Returns:
        Summary of cleanup operation
    """
    try:
        result = await manager.cleanup_outdated_observations()
        logger.debug("🛠️ Tool registered: cleanup_outdated_observations")
        return result.model_dump()
    except Exception as e:
        raise RuntimeError(f"Failed to cleanup observations: {e}")


@mcp.tool
async def get_observations_by_durability(entityName: str) -> Dict[str, Any]:
    """Get observations for an entity grouped by their durability type.
    
    Args:
        entityName: The name of the entity to get observations for
    
    Returns:
        Observations grouped by durability type
    """
    try:
        if not entityName or not isinstance(entityName, str):
            raise ValueError("entityName must be a non-empty string")
        
        result = await manager.get_observations_by_durability(entityName)
        logger.debug("🛠️ Tool registered: get_observations_by_durability")
        return result.model_dump()
    except Exception as e:
        raise RuntimeError(f"Failed to get observations: {e}")


@mcp.tool
async def delete_entities(entityNames: List[str]) -> str:
    """Delete multiple entities and their associated relations from the knowledge graph.
    
    Args:
        entityNames: List of entity names to delete
    
    Returns:
        Success message
    """
    try:
        if not entityNames or not isinstance(entityNames, list):
            raise ValueError("entityNames must be a non-empty list")
        
        await manager.delete_entities(entityNames)
        logger.debug("🛠️ Tool registered: delete_entities")
        return "Entities deleted successfully"
    except Exception as e:
        raise RuntimeError(f"Failed to delete entities: {e}")


@mcp.tool
async def delete_observations(deletions: List[Dict[str, Any]]) -> str:
    """Delete specific observations from entities in the knowledge graph.
    
    Args:
        deletions: List of deletion objects with entityName and observations to delete
    
    Returns:
        Success message
    """
    try:
        deletion_objects = []
        for deletion_data in deletions:
            try:
                deletion_objects.append(DeleteObservationRequest(**deletion_data))
            except Exception as e:
                raise ValueError(f"Invalid deletion data: {e}")
        
        await manager.delete_observations(deletion_objects)
        logger.debug("🛠️ Tool registered: delete_observations")
        return "Observations deleted successfully"
    except Exception as e:
        raise RuntimeError(f"Failed to delete observations: {e}")


@mcp.tool
async def delete_relations(relations: List[Dict[str, str]]) -> str:
    """Delete multiple relations from the knowledge graph.
    
    Args:
        relations: List of relation objects with from, to, and relationType fields
    
    Returns:
        Success message
    """
    try:
        relation_objects = []
        for relation_data in relations:
            try:
                relation_objects.append(Relation(**relation_data))
            except Exception as e:
                raise ValueError(f"Invalid relation data: {e}")
        
        await manager.delete_relations(relation_objects)
        logger.debug("🛠️ Tool registered: delete_relations")
        return "Relations deleted successfully"
    except Exception as e:
        raise RuntimeError(f"Failed to delete relations: {e}")


@mcp.tool
async def read_graph() -> Dict[str, Any]:
    """Read the entire knowledge graph.
    
    Returns:
        Complete knowledge graph data
    """
    try:
        result = await manager.read_graph()
        logger.debug("🛠️ Tool registered: read_graph")
        return result.dict()
    except Exception as e:
        raise RuntimeError(f"Failed to read graph: {e}")


@mcp.tool
async def search_nodes(query: str) -> Dict[str, Any]:
    """Search for nodes in the knowledge graph based on a query.
    
    Args:
        query: The search query to match against entity names, types, and observation content
    
    Returns:
        Search results containing matching nodes
    """
    try:
        if not query or not isinstance(query, str):
            raise ValueError("query must be a non-empty string")
        
        result = await manager.search_nodes(query)
        logger.debug("🛠️ Tool registered: search_nodes")
        return result.dict()
    except Exception as e:
        raise RuntimeError(f"Failed to search nodes: {e}")


@mcp.tool
async def open_nodes(names: List[str]) -> Dict[str, Any]:
    """Open specific nodes in the knowledge graph by their names.
    
    Args:
        names: List of entity names to retrieve
    
    Returns:
        Retrieved node data
    """
    try:
        if not names or not isinstance(names, list):
            raise ValueError("names must be a non-empty list")
        
        result = await manager.open_nodes(names)
        logger.debug("🛠️ Tool registered: open_nodes")
        return result.model_dump()
    except Exception as e:
        raise RuntimeError(f"Failed to open nodes: {e}")


async def main():
    """Common entry point for the MCP server."""
    try:
        logger.info("🧠 Starting IQ-MCP server")
        await mcp.run_async(transport="stdio")
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


def run_sync():
    """Synchronus entry point for the server."""
    logger.debug("Running IQ-MCP from server.py")
    asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())