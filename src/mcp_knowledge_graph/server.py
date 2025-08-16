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
from fastmcp.exceptions import ToolError, ValidationError

from pathlib import Path
from typing import Annotated, Any, Literal

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
)

# Default port for HTTP transport
DEFAULT_PORT = 8000

# Load instructions from instructions.md - these instructions are used to prompt the model by default.


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("iq-mcp")
IQ_DEBUG = bool(os.getenv("IQ_DEBUG", "false").lower() == "true")
if IQ_DEBUG:
    logger.setLevel(logging.DEBUG)


# Define valid FastMCP transport types
Transport = Literal["stdio", "sse", "http"]

TRANSPORT_ENUM: dict[str, Transport] = {
    "stdio": "stdio",
    "http": "http",
    "sse": "sse", 
    "streamable-http": "http",
    "streamableHttp": "http",
    "streamable_http": "http",
    "streamable http": "http",
    "streamablehttp": "http",
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

    # Prefer project root memory.jsonl by default; fallback to example.jsonl
    project_root = Path(__file__).resolve().parents[2]
    default_memory = project_root / "memory.jsonl"
    fallback_example = project_root / "example.jsonl"

    # CLI argument takes precedence
    if args.memory_path:
        memory_path = Path(args.memory_path)
        if memory_path.is_absolute():
            logger.debug(f"🔍 Memory path provided by CLI: {memory_path}")
            return str(memory_path)
        else:
            # Resolve relative to project root
            return str(project_root / memory_path)
    # If no CLI arg, check env var
    elif os.getenv("IQ_MEMORY_PATH"):
        # Environment variable provided
        env_var = os.getenv("IQ_MEMORY_PATH")
        if env_var:  # Check for None to satisfy type checker
            env_path = Path(env_var).resolve()
            return str(env_path)

    # If no CLI arg or env var, use default
    if default_memory.exists():
        return str(default_memory)
    if fallback_example.exists():
        logger.info("📄 Using example.jsonl as memory source (no memory.jsonl found)")
        return str(fallback_example)
    # Final fallback: still point at default path (will be created on write)
    return str(default_memory)


# Initialize the knowledge graph manager and FastMCP server
memory_path = get_memory_file_path()
logger.debug(f"🔍 Memory path: {memory_path}")
manager = KnowledgeGraphManager(memory_path)

# Create FastMCP server instance
mcp = FastMCP(
    name="iq-mcp",
    version="0.1.0"
)


def _ensure_non_empty_string(value: Any, name: str) -> str:
    """Ensure a value is a non-empty string and return it.
    
    Args:
        value: The value to check
        name: The name of the value, for error messages

    Returns:
        The value if it is a non-empty string
    """
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{name} must be a non-empty string")
    return value


def _ensure_string_list(input_data: Any, expected_type: str = "string list") -> list[str]:
    """
    Ensure input is a list[str]. If a JSON string is provided, parse and validate it.
    """
    if isinstance(input_data, str):
        try:
            parsed = json.loads(input_data)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON string for {expected_type}: {e}")
        input_data = parsed

    if not isinstance(input_data, list) or not input_data:
        raise ValidationError(f"{expected_type} must be a non-empty list of strings")

    for i, item in enumerate(input_data):
        if not isinstance(item, str):
            raise ValidationError(
                f"All items in {expected_type} must be strings, item {i} is {type(item).__name__}"
            )
    return input_data


def _build_models_from_dicts(
    items: list[dict[str, Any]],
    model_cls: Any,
    required_fields: set[str],
    item_label: str,
):
    """Validate a list of dicts, ensure required fields, and construct Pydantic models."""
    # Allow JSON string input
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except json.JSONDecodeError as e:
            raise ValidationError(f"Invalid JSON string for {item_label.lower()}s: {e}")

    if not isinstance(items, list) or not items:
        raise ValidationError(f"{item_label.lower()}s must be a non-empty list")

    models = []
    for i, data in enumerate(items):
        if not isinstance(data, dict):
            raise ValidationError(f"{item_label} at index {i} must be an object")

        missing = required_fields - set(data.keys())
        if missing:
            raise ValidationError(f"{item_label} at index {i} missing required fields: {missing}")

        try:
            models.append(model_cls(**data))
        except Exception as e:
            raise ValidationError(f"Invalid {item_label.lower()} data at index {i}: {e}")

    return models

@mcp.tool
async def create_entry(
    entry_type: Annotated[
        Literal["observation", "entity", "relation"],
        "Type of entry to create: 'observation', 'entity', or 'relation'",
    ],
    data: Annotated[
        list[AddObservationRequest] | list[Entity] | list[Relation] | None,
        """Data to be added to the knowledge graph. The data must be a list of the appropriate object for each entry_type:
- observation: [{"entityName": "entityName", "content": list["from": "entityName", "to": "entityName", "relationType": str]}]
- entity: [{"name": "entityName", "entityType": "entityType", "observations": ["content": str, "durability": ["temporary", "short-term", "long-term", "permanent"]]}]
- relation: [{"from": "entityName", "to": "entityName", "relationType": "relationType"}]"""
    ] = None,
) -> list[dict[str, Any]]:
    """Unified creation tool for observations, entities, and relations.

    - entry_type='observation': expects 'data' to be a list of AddObservationRequest objects
    - entry_type='entity': expects 'data' to be a list of Entity objects
    - entry_type='relation': expects 'data' to be a list of Relation objects
    """
    try:
        if entry_type == "observation":
            if not data:
                raise ValidationError("data must be a list of observations to add, with fields: 'entity_name' and 'content'")
            
            # Build AddObservationRequest list using prior validation behavior
            requests: list[AddObservationRequest] = []

            for i, item in enumerate(data):
                if not isinstance(item, AddObservationRequest):
                    raise ValidationError(f"Invalid request at index {i}: must be an AddObservationRequest object")
                requests.append(item)

            result = await manager._apply_observations(requests)
            return [r.model_dump() for r in result]

        # Expect list of Entity dicts list[{"name": "entityName", "entityType": "entityType", "observations": ["content": str, "durability": ["temporary", "short-term", "long-term", "permanent"]]}]
        elif entry_type == "entity":
            # Expect list of Entity dicts
            
            if not data:
                raise ValidationError("data must be a list of entities to add, with fields: 'name', 'entityType', and 'observations'")
            
            entities: list[Entity] = []
            for i, item in enumerate(data):
                if not isinstance(item, Entity):
                    raise ValidationError(f"Invalid request at index {i}: must be an Entity object")
                entities.append(item)

            entity_objects = _build_models_from_dicts(
                data, Entity, {"name", "entityType", "observations"}, "Entity"  # type: ignore[arg-type]
            )
            result = await manager.create_entities(entity_objects)
            logger.debug("🛠️ Tool invoked: create_entry(kind=entity)")
            return [e.model_dump(by_alias=True) for e in result]

        # Expect list of Relation dicts list[{"from": "entityName", "to": "entityName", "relationType": "relationType"}]
        elif entry_type == "relation":
            if isinstance(data, str):
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError as e:
                    raise ValidationError(f"Invalid JSON string for relations: {e}")
                data = parsed
            if not isinstance(data, list) or not data:
                raise ValidationError("data must be a non-empty list of relations")

            relation_objects = _build_models_from_dicts(
                data, Relation, {"from", "to", "relationType"}, "Relation"  # type: ignore[arg-type]
            )
            result = await manager.create_relations(relation_objects)
            logger.debug("🛠️ Tool invoked: create_entry(kind=relation)")
            return [r.model_dump(by_alias=True) for r in result]

        else:
            raise ValidationError("Invalid kind. Must be one of: observation, entity, relation")
    except Exception as e:
        raise ToolError(f"Failed to create entry: {e}")


@mcp.tool
async def cleanup_outdated_observations() -> dict[str, Any]:
    """Remove observations that are likely outdated based on their durability and age.

    Returns:
        Summary of cleanup operation
    """
    try:
        result = await manager.cleanup_outdated_observations()
        logger.debug("🛠️ Tool invoked: cleanup_outdated_observations")
        return result.model_dump()
    except Exception as e:
        raise ToolError(f"Failed to cleanup observations: {e}")


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
        _ensure_non_empty_string(entityName, "entityName")

        result = await manager.get_observations_by_durability(entityName)
        logger.debug("🛠️ Tool invoked: get_observations_by_durability")
        return result.model_dump()
    except Exception as e:
        raise ToolError(f"Failed to get observations: {e}")


@mcp.tool
async def delete_entry(
    kind: Annotated[
        Literal["observation", "entity", "relation"],
        "Type of entry to delete: 'observation', 'entity', or 'relation'",
    ],
    data: Annotated[
        list[dict[str, Any]] | str | None,
        "For batch delete: observation: [{entityName, observations}], relation: [Relation]. Can also be JSON string.",
    ] = None,
    entity_names: Annotated[
        list[str] | str | None,
        "For entity deletion: list of entity names (or JSON string of list)",
    ] = None,
    entity_name: Annotated[
        str | None,
        "Legacy observation form: the name of the entity containing the observations",
    ] = None,
    observations: Annotated[
        list[str] | str | None,
        "Legacy observation form: list (or JSON string) of observation content to delete",
    ] = None,
) -> str:
    """Unified deletion tool for observations, entities, and relations.

    - kind='entity': use 'entity_names' (list or JSON string)
    - kind='observation': supports batch via 'data' or legacy 'entity_name' + 'observations'
    - kind='relation': expects 'data' to be a list or JSON string of Relation objects
    """
    try:
        if kind == "entity":
            # Allow entity_names to be provided as list or JSON string
            if entity_names is None and isinstance(data, (list, str)):
                # Be flexible: allow using 'data' for entity names as well
                entity_names = data  # type: ignore[assignment]
            names = _ensure_string_list(entity_names, "entity_names")  # type: ignore[arg-type]
            await manager.delete_entities(names)
            logger.debug("🛠️ Tool invoked: delete_entry(kind=entity)")
            return "Entities deleted successfully"

        elif kind == "observation":
            requests: list[DeleteObservationRequest] = []

            if entity_name is not None or observations is not None:
                _ensure_non_empty_string(entity_name, "entity_name")  # type: ignore[arg-type]
                obs_list = _ensure_string_list(observations, "observations")  # type: ignore[arg-type]
                requests = [
                    DeleteObservationRequest(entity_name=entity_name, observations=obs_list)  # type: ignore[arg-type]
                ]
            else:
                if isinstance(data, str):
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError as e:
                        raise ValidationError(f"Invalid JSON string for deletions: {e}")

                if not isinstance(data, list) or not data:
                    raise ValidationError("data must be a non-empty list of deletion requests")

                for i, item in enumerate(data):
                    if not isinstance(item, dict):
                        raise ValidationError(f"Request at index {i} must be an object")
                    if "entityName" not in item or "observations" not in item:
                        raise ValidationError(
                            f"Request at index {i} missing required fields: 'entityName' and 'observations'"
                        )
                    name = _ensure_non_empty_string(item["entityName"], "entityName")
                    obs_list = _ensure_string_list(item["observations"], "observations")
                    requests.append(
                        DeleteObservationRequest(entity_name=name, observations=obs_list)
                    )

            await manager.delete_observations(requests)
            logger.debug("🛠️ Tool invoked: delete_entry(kind=observation)")
            return "Observations deleted successfully"

        elif kind == "relation":
            if isinstance(data, str):
                try:
                    parsed = json.loads(data)
                except json.JSONDecodeError as e:
                    raise ValidationError(f"Invalid JSON string for relations: {e}")
                data = parsed
            if not isinstance(data, list) or not data:
                raise ValidationError("data must be a non-empty list of relations")

            relation_objects = _build_models_from_dicts(
                data, Relation, {"from", "to", "relationType"}, "Relation"
            )
            await manager.delete_relations(relation_objects)
            logger.debug("🛠️ Tool invoked: delete_entry(kind=relation)")
            return "Relations deleted successfully"

        else:
            raise ValidationError("Invalid kind. Must be one of: observation, entity, relation")
    except Exception as e:
        raise ToolError(f"Failed to delete entry: {e}")


@mcp.tool
async def read_graph() -> dict[str, Any]:
    """# ***CRITICAL: USE THIS TOOL FIRST AT THE BEGINNING OF EACH CONVERSATION!!!***
    Read the entire knowledge graph.

    Returns:
        Complete knowledge graph data in JSON format
    """
    try:
        result = await manager.read_graph()
        logger.debug("🛠️ Tool invoked: read_graph")
        return result.model_dump(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to read graph: {e}")


@mcp.tool
async def search_nodes(
    query: Annotated[
        str, "The search query to match against entity names, types, and observation content"
    ],
) -> dict[str, Any]:
    """Search for nodes in the knowledge graph based on a query.

    Args:
        query: The search query to match against entity names, types, and/or observation content

    Returns:
        Search results containing matching nodes
    """
    try:
        if not query or not isinstance(query, str):
            raise ValidationError("query must be a non-empty string")

        result = await manager.search_nodes(query)
        logger.debug("🛠️ Tool invoked: search_nodes")
        return result.model_dump(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to search nodes: {e}")


@mcp.tool
async def open_nodes(
    entity_names: Annotated[list[str], "List of entity names to retrieve"],
) -> dict[str, Any]:
    """Open specific nodes in the knowledge graph by their names.

    Args:
        entity_names: List of entity names to retrieve

    Returns:
        Retrieved node data
    """
    try:
        names = _ensure_string_list(entity_names, "entity_names")
        result = await manager.open_nodes(names)
        logger.debug("🛠️ Tool invoked: open_nodes")
        return result.model_dump(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to open nodes: {e}")


@mcp.tool
async def merge_entities(
    newEntityName: Annotated[str, "Name of the new merged entity (typically the first in the list)"],
    entityNames: Annotated[list[str] | str, "Names of entities to merge into the new entity"],
) -> dict[str, Any]:
    """Merge a list of entities into a new entity with the provided name.

    The manager will combine observations and update relations to point to the new entity.
    """
    try:
        _ensure_non_empty_string(newEntityName, "newEntityName")

        names = _ensure_string_list(entityNames, "entity names")
        if not names:
            raise ValidationError("entityNames must contain at least one name")

        merged = await manager.merge_entities(newEntityName, names)
        logger.debug("🛠️ Tool invoked: merge_entities")
        return merged.dict(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to merge entities: {e}")


async def start_server():
    """Common entry point for the MCP server."""
    transport = os.getenv("IQ_TRANSPORT", "stdio")
    
    # Validate and normalize the transport type
    transport_key = transport.lower().strip()
    if transport_key not in TRANSPORT_ENUM:
        raise ValueError(f"Invalid transport specified: '{transport}'. Valid options: stdio, streamable-http, sse")
    
    validated_transport: Transport = TRANSPORT_ENUM[transport_key]
    logger.debug(f"🆗 Transport validated: {transport} -> {validated_transport}")

    # Get transport-specific configuration
    if validated_transport == "http":
        transport_kwargs = {
            "host": os.getenv("IQ_STREAMABLE_HTTP_HOST"),
            "port": int(os.getenv("IQ_STREAMABLE_HTTP_PORT", DEFAULT_PORT)),
            "path": os.getenv("IQ_STREAMABLE_HTTP_PATH"),
            "log_level": "debug" if IQ_DEBUG else "info"
        }
    else:
        transport_kwargs = {}

    try:
        await mcp.run_async(transport=validated_transport, **transport_kwargs)
    except Exception as e:
        print(f"Server error: {e}", file=sys.stderr)
        sys.exit(1)

def run_sync():
    """Synchronus entry point for the server."""
    logger.debug("Running IQ-MCP from server.py")
    asyncio.run(start_server())

if __name__ == "__main__":
    asyncio.run(start_server())
