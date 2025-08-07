"""
FastMCP Server implementation for temporal knowledge graph memory.

This module implements the Model Context Protocol server that exposes
knowledge graph operations as tools for LLM integration using FastMCP 2.11.
"""

import argparse
import asyncio
import json
import os
import sys
import logging

from pathlib import Path
from typing import Annotated, Any, Literal, Union

from fastmcp import FastMCP

# Load .env file if available to ensure environment variables are accessible
try:
    from dotenv import load_dotenv

    load_dotenv(verbose=False)  # Silent loading to avoid duplicate log messages
except ImportError:
    pass  # dotenv is optional

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


# Define valid FastMCP transport types
Transport = Literal["stdio", "sse", "streamable-http"]

TRANSPORT_ENUM: dict[str, Transport] = {
    "stdio": "stdio",
    "http": "streamable-http",
    "sse": "sse", 
    "streamable-http": "streamable-http",
    "streamableHttp": "streamable-http",
    "streamable_http": "streamable-http",
    "streamable http": "streamable-http",
    "streamablehttp": "streamable-http",
}

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Temporal-Enhanced MCP Knowledge Graph Server")
    parser.add_argument(
        "--memory-path",
        type=str,
        help="Custom path for memory storage (overrides IQ_MEMORY_PATH env var)",
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
            logger.debug(f"🔍 Memory path provided by CLI: {memory_path}")
            return str(memory_path)
        else:
            return str(Path(__file__).parent.parent / memory_path)

    elif os.getenv("IQ_MEMORY_PATH"):
        # Environment variable provided
        env_var = os.getenv("IQ_MEMORY_PATH")
        if env_var:  # Check for None to satisfy type checker
            env_path = Path(env_var)
            logger.debug(f"🔍 Memory path provided by env: {env_path}")
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


def _validate_and_parse_input(
    input_data: list[dict[str, Any]] | str, expected_type: str
) -> list[dict[str, Any]]:
    """
    Validate and parse input data, converting JSON strings to list of dictionaries.

    Args:
        input_data: Either a list of dictionaries or a JSON string
        expected_type: Description of expected type for error messages

    Returns:
        List of dictionaries ready for model validation

    Raises:
        ValueError: If input cannot be parsed or validated
    """
    if isinstance(input_data, str):
        try:
            parsed_data = json.loads(input_data)
            if not isinstance(parsed_data, list):
                raise ValueError(
                    f"String input must parse to a list, got {type(parsed_data).__name__}"
                )
            return parsed_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for {expected_type}: {e}")
    elif isinstance(input_data, list):
        return input_data
    else:
        raise ValueError(f"Input must be a list or JSON string, got {type(input_data).__name__}")


def _validate_and_parse_string_list(input_data: list[str] | str, expected_type: str) -> list[str]:
    """
    Validate and parse input data, converting JSON strings to list of strings.

    Args:
        input_data: Either a list of strings or a JSON string
        expected_type: Description of expected type for error messages

    Returns:
        List of strings ready for processing

    Raises:
        ValueError: If input cannot be parsed or validated
    """
    if isinstance(input_data, str):
        try:
            parsed_data = json.loads(input_data)
            if not isinstance(parsed_data, list):
                raise ValueError(
                    f"String input must parse to a list, got {type(parsed_data).__name__}"
                )

            # Validate all items are strings
            for i, item in enumerate(parsed_data):
                if not isinstance(item, str):
                    raise ValueError(
                        f"All list items must be strings, item {i} is {type(item).__name__}"
                    )

            return parsed_data
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON string for {expected_type}: {e}")
    elif isinstance(input_data, list):
        # Validate all items are strings
        for i, item in enumerate(input_data):
            if not isinstance(item, str):
                raise ValueError(
                    f"All list items must be strings, item {i} is {type(item).__name__}"
                )
        return input_data
    else:
        raise ValueError(f"Input must be a list or JSON string, got {type(input_data).__name__}")


def _validate_and_parse_entities(input_data: list[dict[str, Any]] | str) -> list[Entity]:
    """
    Validate and parse Entity objects from input data.

    Args:
        input_data: Either a list of entity dictionaries or a JSON string

    Returns:
        List of validated Entity objects

    Raises:
        ValueError: If validation fails
    """
    entities_data = _validate_and_parse_input(input_data, "entity objects")

    entity_objects = []
    for i, entity_data in enumerate(entities_data):
        try:
            entity_objects.append(Entity(**entity_data))
        except Exception as e:
            raise ValueError(f"Invalid entity data at index {i}: {e}")

    return entity_objects


def _validate_and_parse_relations(input_data: list[dict[str, Any]] | str) -> list[Relation]:
    """
    Validate and parse Relation objects from input data.

    Args:
        input_data: Either a list of relation dictionaries or a JSON string

    Returns:
        List of validated Relation objects

    Raises:
        ValueError: If validation fails
    """
    relations_data = _validate_and_parse_input(input_data, "relation objects")

    relation_objects = []
    for i, relation_data in enumerate(relations_data):
        try:
            relation_objects.append(Relation(**relation_data))
        except Exception as e:
            raise ValueError(f"Invalid relation data at index {i}: {e}")

    return relation_objects


def _validate_and_parse_add_observations(
    input_data: list[dict[str, Any]] | str,
) -> list[AddObservationRequest]:
    """
    Validate and parse AddObservationRequest objects from input data.

    Args:
        input_data: Either a list of observation request dictionaries or a JSON string

    Returns:
        List of validated AddObservationRequest objects

    Raises:
        ValueError: If validation fails
    """
    observations_data = _validate_and_parse_input(input_data, "observation objects")

    requests = []
    for i, obs_data in enumerate(observations_data):
        try:
            if "entityName" not in obs_data or "contents" not in obs_data:
                raise ValueError("Missing required fields: entityName and contents")

            # Handle mixed content types (strings and objects)
            contents = []
            for j, content in enumerate(obs_data["contents"]):
                if isinstance(content, str):
                    contents.append(content)
                elif isinstance(content, dict):
                    try:
                        contents.append(ObservationInput(**content))
                    except Exception as e:
                        raise ValueError(f"Invalid observation content at index {j}: {e}")
                else:
                    raise ValueError(f"Invalid content type at index {j}: {type(content)}")

            requests.append(
                AddObservationRequest(entity_name=obs_data["entityName"], contents=contents)
            )
        except Exception as e:
            raise ValueError(f"Invalid observation request at index {i}: {e}")

    return requests


def _validate_and_parse_delete_observations(
    input_data: list[dict[str, Any]] | str,
) -> list[DeleteObservationRequest]:
    """
    Validate and parse DeleteObservationRequest objects from input data.

    Args:
        input_data: Either a list of deletion request dictionaries or a JSON string

    Returns:
        List of validated DeleteObservationRequest objects

    Raises:
        ValueError: If validation fails
    """
    deletions_data = _validate_and_parse_input(input_data, "deletion objects")

    deletion_objects = []
    for i, deletion_data in enumerate(deletions_data):
        try:
            deletion_objects.append(DeleteObservationRequest(**deletion_data))
        except Exception as e:
            raise ValueError(f"Invalid deletion data at index {i}: {e}")

    return deletion_objects


@mcp.tool
async def create_entities(
    entities: Annotated[
        list[dict[str, Any]] | str,
        "List of entity objects with name, entityType, and observations fields",
    ],
) -> list[dict[str, Any]] | str:
    """Create multiple new entities in the knowledge graph.

    Args:
        entities: List of entity objects with name, entityType, and observations

    Returns:
        List of created entity objects
    """
    try:
        entity_objects = _validate_and_parse_entities(entities)
        result = await manager.create_entities(entity_objects)
        logger.debug("🛠️ Tool registered: create_entities")
        return [e.dict() for e in result]
    except Exception as e:
        raise RuntimeError(f"Failed to create entities: {e}")


@mcp.tool
async def create_relations(
    relations: Annotated[
        list[dict[str, Any]] | str,
        "List of relation objects with from, to, and relationType fields",
    ],
) -> list[dict[str, Any]] | str:
    """Create multiple new relations between entities in the knowledge graph. Relations should be in active voice.

    Args:
        relations: List of relation objects with from, to, and relationType fields

    Returns:
        List of created relation objects
    """
    try:
        relation_objects = _validate_and_parse_relations(relations)
        result = await manager.create_relations(relation_objects)
        logger.debug("🛠️ Tool registered: create_relations")
        return [r.dict() for r in result]
    except Exception as e:
        raise RuntimeError(f"Failed to create relations: {e}")


@mcp.tool
async def add_observations(
    observations: Annotated[
        list[dict[str, Any]] | str,
        "List of observation objects with entityName and contents fields",
    ],
) -> list[dict[str, Any]] | str:
    """Add new observations to existing entities in the knowledge graph. Supports both simple strings and temporal observations with durability metadata (permanent, long-term, short-term, temporary).

    Args:
        observations: List of observation objects with entityName and contents (can be strings or objects with durability)

    Returns:
        List of processed observation request objects
    """
    try:
        requests = _validate_and_parse_add_observations(observations)
        result = await manager.add_observations(requests)
        logger.debug("🛠️ Tool registered: add_observations")
        return [r.model_dump() for r in result]
    except Exception as e:
        raise RuntimeError(f"Failed to add observations: {e}")


@mcp.tool
async def cleanup_outdated_observations() -> dict[str, Any]:
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
async def get_observations_by_durability(
    entityName: Annotated[str, "The name of the entity to get observations for"],
) -> dict[str, Any]:
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
async def delete_entities(
    entityNames: Annotated[
        list[str] | str, "List of entity names to delete, or JSON string representing a list"
    ],
) -> str:
    """Delete multiple entities and their associated relations from the knowledge graph.

    Args:
        entityNames: List of entity names to delete, or JSON string representing a list

    Returns:
        Success message
    """
    try:
        # Validate and parse input
        entity_names = _validate_and_parse_string_list(entityNames, "entity names")

        if not entity_names:
            raise ValueError("entityNames must be a non-empty list")

        await manager.delete_entities(entity_names)
        logger.debug("🛠️ Tool registered: delete_entities")
        return "Entities deleted successfully"
    except Exception as e:
        raise RuntimeError(f"Failed to delete entities: {e}")


@mcp.tool
async def delete_observations(
    deletions: Annotated[
        list[dict[str, Any]] | str,
        "List of deletion objects with entityName and observations fields",
    ],
) -> str:
    """Delete specific observations from entities in the knowledge graph.

    Args:
        deletions: List of deletion objects with entityName and observations to delete

    Returns:
        Success message
    """
    try:
        deletion_objects = _validate_and_parse_delete_observations(deletions)
        await manager.delete_observations(deletion_objects)
        logger.debug("🛠️ Tool registered: delete_observations")
        return "Observations deleted successfully"
    except Exception as e:
        raise RuntimeError(f"Failed to delete observations: {e}")


@mcp.tool
async def delete_relations(
    relations: Annotated[
        list[dict[str, Any]] | str,
        "List of relation objects with from, to, and relationType fields",
    ],
) -> str:
    """Delete multiple relations from the knowledge graph.

    Args:
        relations: List of relation objects with from, to, and relationType fields

    Returns:
        Success message
    """
    try:
        relation_objects = _validate_and_parse_relations(relations)
        await manager.delete_relations(relation_objects)
        logger.debug("🛠️ Tool registered: delete_relations")
        return "Relations deleted successfully"
    except Exception as e:
        raise RuntimeError(f"Failed to delete relations: {e}")


@mcp.tool
async def read_graph() -> dict[str, Any]:
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
async def search_nodes(
    query: Annotated[
        str, "The search query to match against entity names, types, and observation content"
    ],
) -> dict[str, Any]:
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
async def open_nodes(
    names: Annotated[
        list[str] | str, "List of entity names to retrieve, or JSON string representing a list"
    ],
) -> dict[str, Any]:
    """Open specific nodes in the knowledge graph by their names.

    Args:
        names: List of entity names to retrieve, or JSON string representing a list

    Returns:
        Retrieved node data
    """
    try:
        # Validate and parse input
        entity_names = _validate_and_parse_string_list(names, "entity names")

        if not entity_names:
            raise ValueError("names must be a non-empty list")

        result = await manager.open_nodes(entity_names)
        logger.debug("🛠️ Tool registered: open_nodes")
        return result.model_dump()
    except Exception as e:
        raise RuntimeError(f"Failed to open nodes: {e}")


async def start_server():
    """Common entry point for the MCP server."""
    transport = os.getenv("IQ_TRANSPORT", "stdio")
    
    # Validate and normalize the transport type
    transport_key = transport.lower().strip()
    if transport_key not in TRANSPORT_ENUM:
        raise ValueError(f"Invalid transport specified: '{transport}'. Valid options: stdio, streamable-http, sse")
    
    validated_transport: Transport = TRANSPORT_ENUM[transport_key]
    logger.debug(f"🆗 Transport validated: {transport} -> {validated_transport}")

    try:
        logger.info(f"🧠 Starting IQ-MCP server with transport: {validated_transport}")
        await mcp.run_async(transport=validated_transport)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)


def run_sync():
    """Synchronus entry point for the server."""
    logger.debug("Running IQ-MCP from server.py")
    asyncio.run(start_server())


if __name__ == "__main__":
    asyncio.run(start_server())
