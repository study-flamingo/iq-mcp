"""
FastMCP Server implementation for temporal knowledge graph memory.

This module implements the Model Context Protocol server that exposes
knowledge graph operations as tools for LLM integration using FastMCP 2.11.
"""

import asyncio
import json
import sys
import logging
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from pathlib import Path
from typing import Any, Literal
from fastmcp.exceptions import ToolError, ValidationError

from .manager import KnowledgeGraphManager
from .models import (
    Entity,
    Relation,
    AddObservationRequest,
    DeleteObservationRequest,
)
from .settings import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("iq-mcp")


# Load settings once and configure logging level accordingly


# Initialize the knowledge graph manager and FastMCP server
logger.debug(f"🔍 Memory path: {settings.memory_path}")
manager = KnowledgeGraphManager(settings.memory_path)

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

class CreateEntryRequest(BaseModel):
    entry_type: Literal["observation", "entity", "relation"] = Field(description="Type of entry to create: 'observation', 'entity', or 'relation'")
    data: list[AddObservationRequest] | list[Entity] | list[Relation] | None = Field(
        description="""Data to be added to the knowledge graph. 
        
        'data' must be a list of the appropriate object for each entry_type:
    
        - observation: [{'entity_name': 'entity_name', 'content': list['from': 'entity_name', 'to': 'entity_name', 'relationType': str]]
        - entity: [{'name': 'entity_name', 'entity_type': 'entity_type', 'observations': [{'content': str, 'durability': ['temporary', 'short-term', 'long-term', 'permanent']}]}]
        - relation: [{'from': 'entity_name', 'to': 'entity_name', 'relationType': 'relationType'}]
         """)

@mcp.tool
async def create_entry(request: CreateEntryRequest) -> list[dict[str, Any]]:
    """Add entities, observations, or relations to the knowledge graph.
    
    'data' must be a list of the appropriate object for each entry_type:
    
    - observation: [{'entity_name': 'entity_name', 'content': list['from': 'entity_name', 'to': 'entity_name', 'relationType': str]]
    - entity: [{'name': 'entity_name', 'entity_type': 'entity_type', 'observations': [{'content': str, 'durability': ['temporary', 'short-term', 'long-term', 'permanent']}]}]
    - relation: [{'from': 'entity_name', 'to': 'entity_name', 'relationType': 'relationType'}]
    """
    entry_type = request.entry_type
    data = request.data

    try:
        if entry_type == "observation":
            # Validate data is a list of AddObservationRequest objects
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

        # Expect list of Entity dicts list[{"name": "entity_name", "entity_type": "entity_type", "observations": ["content": str, "durability": ["temporary", "short-term", "long-term", "permanent"]]}]
        elif entry_type == "entity":
            # Validate data is a list of Entity objects
            if not data:
                raise ValidationError("data must be a list of entities to add, with fields: 'name', 'entity_type', and 'observations'")
            
            entities: list[Entity] = []
            for i, item in enumerate(data):
                if not isinstance(item, Entity):
                    raise ValidationError(f"Invalid request at index {i}: must be an Entity object")
                entities.append(item)

            entity_objects = _build_models_from_dicts(
                data, Entity, {"name", "entity_type", "observations"}, "Entity"  # type: ignore[arg-type]
            )
            result = await manager.create_entities(entity_objects)
            logger.debug("🛠️ Tool invoked: create_entry(kind=entity)")
            return [e.model_dump(by_alias=True) for e in result]

        # Expect list of Relation dicts list[{"from": "entity_name", "to": "entity_name", "relationType": "relationType"}]
        elif entry_type == "relation":
            # Validate data is a list of Relation objects
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
            logger.debug("🛠️ Tool invoked: create_entry")
            return [r.model_dump(by_alias=True) for r in result]

        else:
            raise ValidationError("Invalid entry_type. Must be one of: observation, entity, relation")
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
    entity_name: str = Field(description="The name of the entity to get observations for"),
) -> dict[str, Any]:
    """Get observations for an entity grouped by their durability type.

    Args:
        entity_name: The name of the entity to get observations for

    Returns:
        Observations grouped by durability type
    """
    try:
        _ensure_non_empty_string(entity_name, "entity_name")

        result = await manager.get_observations_by_durability(entity_name)
        logger.debug("🛠️ Tool invoked: get_observations_by_durability")
        return result.model_dump()
    except Exception as e:
        raise ToolError(f"Failed to get observations: {e}")

class DeleteEntryRequest(BaseModel):
    entry_type: Literal["observation", "entity", "relation"] = Field(description="Type of entry to create: 'observation', 'entity', or 'relation'")
    data: list[AddObservationRequest] | list[str] | list[Relation] | None = Field(
        description="""Data to be PERMANENTLY deleted from the knowledge graph. The data must be a list of the appropriate object for each entry_type:
        - observation: [{'entity_name': 'entity_name', 'content': 'observation_content'}]
        - entity: [list_of_entity_names]
        - relation: [{'from': 'entity_name', 'to': 'entity_name', 'relationType': 'relationType'}]
        """)

@mcp.tool
async def delete_entry(request: DeleteEntryRequest) -> str:
    """Unified deletion tool for observations, entities, and relations. Data must be a list of the appropriate object for each entry_type:

    - entry_type = 'entity': list of entity names
    - entry_type = 'observation': [{entity_name, [observation content]}]
    - entry_type = 'relation': [{from_entity, to_entity, relation_type}]

    ***CRITICAL: THIS ACTION IS DESTRUCTIVE AND IRREVERSIBLE - ENSURE USER CONSENTS BEFORE USE!!!***
    """
    entry_type = request.entry_type
    data = request.data

    try:
        if entry_type == "entity":
            # Allow entity_names to be provided as list or JSON string
            if not data or not isinstance(data, list[str]):
                raise ValidationError("data must be a non-empty list of entity names")

            logger.debug("🛠️ Tool invoked: delete_entry(kind=entity)")
            try:
                await manager.delete_entities(data)
            except Exception as e:
                raise ToolError(f"Failed to delete entities: {e}")

            return "Entities deleted successfully"

        elif entry_type == "observation":
            requests: list[DeleteObservationRequest] = []

            if data is not None:
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
                    if "entity_name" not in item or "observations" not in item:
                        raise ValidationError(
                            f"Request at index {i} missing required fields: 'entity_name' and 'observations'"
                        )
                    name = _ensure_non_empty_string(item["entity_name"], "entity_name")
                    obs_list = _ensure_string_list(item["observations"], "observations")
                    requests.append(
                        DeleteObservationRequest(entity_name=name, observations=obs_list)
                    )

            await manager.delete_observations(requests)
            logger.debug("🛠️ Tool invoked: delete_entry(kind=observation)")
            return "Observations deleted successfully"

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
                data, Relation, {"from", "to", "relationType"}, "Relation"
            )
            await manager.delete_relations(relation_objects)
            logger.debug("🛠️ Tool invoked: delete_entry(kind=relation)")
            return "Relations deleted successfully"

        else:
            raise ValidationError("Invalid entry_type. Must be one of: observation, entity, relation")
    except Exception as e:
        raise ToolError(f"Failed to delete entry: {e}")


@mcp.tool
async def read_graph() -> dict[str, Any]:
    """Read the entire knowledge graph.

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
    query: str = Field(description="The search query to match against entity names, types, and observation content"),
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
    entity_names: list[str] = Field(description="List of entity names to retrieve"),
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
    newentity_name: str = Field(description="Name of the new merged entity (typically the first in the list)"),
    entity_names: list[str] | str = Field(description="Names of entities to merge into the new entity"),
) -> dict[str, Any]:
    """Merge a list of entities into a new entity with the provided name.

    The manager will combine observations and update relations to point to the new entity.
    """
    try:
        _ensure_non_empty_string(newentity_name, "newentity_name")

        names = _ensure_string_list(entity_names, "entity names")
        if not names:
            raise ValidationError("entity_names must contain at least one name")

        merged = await manager.merge_entities(newentity_name, names)
        logger.debug("🛠️ Tool invoked: merge_entities")
        return merged.dict(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to merge entities: {e}")


async def start_server():
    """Common entry point for the MCP server."""
    validated_transport = settings.transport
    logger.debug(f"🚌 Transport selected: {validated_transport}")
    if validated_transport == "http":
        transport_kwargs = {
            "host": settings.streamable_http_host,
            "port": settings.port,
            "path": settings.streamable_http_path,
            "log_level": "debug" if settings.debug else "info",
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
