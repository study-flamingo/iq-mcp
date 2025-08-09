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
    ObservationInput,
)

# Default port for HTTP transport
DEFAULT_PORT = 8000

# Load instructions from instructions.md - these instructions are used to prompt the model by default.
with open("instructions.md", "r") as file:
    IQ_INSTRUCTIONS = file.read()


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
    version="0.1.0",
    instructions=IQ_INSTRUCTIONS
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
    items: list[dict[str, Any]] | str,
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
async def add_observations(
    data: Annotated[
        list[dict[str, Any]] | str | None,
        "Either a list of request objects or a JSON string of that list. Each item: {entityName, contents}.",
    ] = None,
    entity_name: Annotated[
        str | None, "The name of the entity to add observations to (legacy single-entity form)"
    ] = None,
    observations: Annotated[
        list[str] | list[dict[str, Any]] | None,
        "List of observation strings or objects with 'content' and optional 'durability' fields (legacy single-entity form)",
    ] = None,
) -> list[dict[str, Any]]:
    """Add observations to entities.

    Supports two forms:
    - Batch: data=[{entityName, contents:[...]}] or JSON string of that list
    - Single-entity (legacy): entity_name + observations
    """
    try:
        requests: list[AddObservationRequest] = []

        if entity_name is not None or observations is not None:
            # Legacy single-entity path
            _ensure_non_empty_string(entity_name, "entity_name")  # type: ignore[arg-type]
            if not isinstance(observations, list) or not observations:  # type: ignore[unreachable]
                raise ValidationError("observations must be a non-empty list")

            obs_list: list[ObservationInput] = []  # type: ignore[arg-type]
            for i, obs in enumerate(observations):
                if isinstance(obs, str):
                    obs_list.append(ObservationInput(content=obs))
                elif isinstance(obs, dict):
                    if "content" not in obs or obs.get("content") is None:
                        raise ValidationError(
                            f"Observation object at index {i} must have a 'content' field"
                        )
                    obs_list.append(ObservationInput(**obs))
                else:
                    raise ValidationError(
                        f"Observation at index {i} must be a string or object with 'content' field"
                    )

            requests = [AddObservationRequest(entity_name=entity_name, contents=obs)]  # type: ignore[arg-type]

        else:
            # Batch path: expect list or JSON string
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError as e:
                    raise ValidationError(f"Invalid JSON string for observations: {e}")

            if not isinstance(data, list) or not data:
                raise ValidationError("data must be a non-empty list of observation requests")

            for i, item in enumerate(data):
                if not isinstance(item, dict):
                    raise ValidationError(f"Request at index {i} must be an object")
                if "entityName" not in item or "contents" not in item:
                    raise ValidationError(
                        f"Request at index {i} missing required fields: 'entityName' and 'contents'"
                    )

                name = _ensure_non_empty_string(item["entityName"], "entityName")
                contents_raw = item["contents"]
                if not isinstance(contents_raw, list) or not contents_raw:
                    raise ValidationError("contents must be a non-empty list")

                obs_list: list[ObservationInput] = []
                for j, obs in enumerate(contents_raw):
                    if isinstance(obs, str):
                        obs_list.append(ObservationInput(content=obs))
                    elif isinstance(obs, dict):
                        if "content" not in obs:
                            raise ValidationError(
                                f"Observation object at index {j} must have a 'content' field"
                            )
                        obs_list.append(ObservationInput(**obs))
                    else:
                        raise ValidationError(
                            f"Observation at index {j} must be a string or object with 'content' field"
                        )

                requests.append(AddObservationRequest(entity_name=name, contents=obs_list))

        result = await manager.add_observations(requests)
        logger.debug("🛠️ Tool invoked: add_observations")
        return [r.model_dump() for r in result]
    except Exception as e:
        raise ToolError(f"Failed to add observations: {e}")


@mcp.tool
async def create_entities(
    entities: Annotated[
        list[dict[str, Any]],
        "List of entity objects with 'name', 'entityType', and 'observations' fields",
    ],
) -> list[dict[str, Any]]:
    """Create multiple new entities in the knowledge graph.

    Args:
        entities: List of entity objects with name, entityType, and observations

    Returns:
        List of created entity objects
    """
    try:
        entity_objects = _build_models_from_dicts(
            entities, Entity, {"name", "entityType", "observations"}, "Entity"
        )
        result = await manager.create_entities(entity_objects)
        logger.debug("🛠️ Tool invoked: create_entities")
        return [e.model_dump(by_alias=True) for e in result]
    except Exception as e:
        raise ToolError(f"Failed to create entities: {e}")


@mcp.tool
async def create_relations(
    relations: Annotated[
        list[dict[str, Any]],
        "List of relation objects with 'from', 'to', and 'relationType' fields",
    ],
) -> list[dict[str, Any]]:
    """Create multiple new relations between entities in the knowledge graph. Relations should be in active voice.

    Args:
        relations: List of relation objects with from, to, and relationType fields

    Returns:
        List of created relation objects
    """
    try:
        relation_objects = _build_models_from_dicts(
            relations, Relation, {"from", "to", "relationType"}, "Relation"
        )
        result = await manager.create_relations(relation_objects)
        logger.debug("🛠️ Tool invoked: create_relations")
        return [r.model_dump(by_alias=True) for r in result]
    except Exception as e:
        raise ToolError(f"Failed to create relations: {e}")


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
async def delete_entities(
    entity_names: Annotated[list[str], "List of entity names to delete"],
) -> str:
    """Delete multiple entities and their associated relations from the knowledge graph.

    Args:
        entity_names: List of entity names to delete

    Returns:
        Success message
    """
    try:
        names = _ensure_string_list(entity_names, "entity_names")
        await manager.delete_entities(names)
        logger.debug("🛠️ Tool invoked: delete_entities")
        return "Entities deleted successfully"
    except Exception as e:
        raise ToolError(f"Failed to delete entities: {e}")


@mcp.tool
async def delete_observations(
    data: Annotated[
        list[dict[str, Any]] | str | None,
        "Either a list of deletion request objects or JSON string of that list. Each item: {entityName, observations}.",
    ] = None,
    entity_name: Annotated[
        str | None, "The name of the entity containing the observations (legacy single-entity form)"
    ] = None,
    observations: Annotated[
        list[str] | str | None, "List of observation contents to delete (legacy single-entity form)"
    ] = None,
) -> str:
    """Delete specific observations. Supports batch or single-entity forms."""
    try:
        requests: list[DeleteObservationRequest] = []

        if entity_name is not None or observations is not None:
            _ensure_non_empty_string(entity_name, "entity_name")  # type: ignore[arg-type]
            obs_list = _ensure_string_list(observations, "observations")  # type: ignore[arg-type]
            requests = [DeleteObservationRequest(entity_name=entity_name, observations=obs_list)]  # type: ignore[arg-type]
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
        logger.debug("🛠️ Tool invoked: delete_observations")
        return "Observations deleted successfully"
    except Exception as e:
        raise ToolError(f"Failed to delete observations: {e}")


@mcp.tool
async def delete_relations(
    relations: Annotated[
        list[dict[str, Any]],
        "List of relation objects with 'from', 'to', and 'relationType' fields",
    ],
) -> str:
    """Delete multiple relations from the knowledge graph.

    Args:
        relations: List of relation objects with from, to, and relationType fields

    Returns:
        Success message
    """
    try:
        relation_objects = _build_models_from_dicts(
            relations, Relation, {"from", "to", "relationType"}, "Relation"
        )
        await manager.delete_relations(relation_objects)
        logger.debug("🛠️ Tool invoked: delete_relations")
        return "Relations deleted successfully"
    except Exception as e:
        raise ToolError(f"Failed to delete relations: {e}")


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
