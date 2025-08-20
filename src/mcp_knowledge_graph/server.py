"""
FastMCP Server implementation for temporal knowledge graph memory.

This module implements the Model Context Protocol server that exposes
knowledge graph operations as tools for LLM integration using FastMCP 2.11.
"""

import asyncio
import logging
from fastmcp import FastMCP
from pydantic import Field
from typing import Any
from fastmcp.exceptions import ToolError, ValidationError

from .manager import KnowledgeGraphManager
from .models import (
    CreateEntryRequest,
    DeleteEntryRequest,
)
from .settings import settings
from src.iq_notify.notify import supabase, EmailSummary

import datetime
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("iq-mcp")


# Load settings once and configure logging level accordingly


# Initialize the knowledge graph manager and FastMCP server
logger.debug(f"🔍 Memory path: {settings.memory_path}")
manager = KnowledgeGraphManager(settings.memory_path)

# Create FastMCP server instance
mcp = FastMCP(name="iq-mcp", version="0.1.0")


@mcp.tool
async def create_entry(request: CreateEntryRequest) -> list[dict[str, Any]]:
    """Add entities, observations, or relations to the knowledge graph.

    'data' must be a list of the appropriate object for each entry_type:

    - observation: [{'entity_name': 'entity_name_or_alias', 'content': [...]}]
    - entity: [{'name': 'entity_name', 'entity_type': 'entity_type', 'observations': [{'content': str, 'durability': ['temporary', 'short-term', 'long-term', 'permanent']}], 'aliases': ['alt1', 'alt2', ...]}]
    - relation: [{'from': 'entity_name_or_alias', 'to': 'entity_name_or_alias', 'relation_type': 'relation_type'}]

    Aliases are resolved to canonical entity names by the manager.
    """
    entry_type = request.entry_type
    data = request.data

    try:
        if entry_type == "observation":
            result = await manager.apply_observations(data)  # type: ignore[arg-type]
            return [r.model_dump() for r in result]
        elif entry_type == "entity":
            result = await manager.create_entities(data)  # type: ignore[arg-type]
            logger.debug("🛠️ Tool invoked: create_entry(kind=entity)")
            return [e.model_dump(by_alias=True) for e in result]
        elif entry_type == "relation":
            result = await manager.create_relations(data)  # type: ignore[arg-type]
            logger.debug("🛠️ Tool invoked: create_entry")
            return [r.model_dump(by_alias=True) for r in result]
        else:
            return []
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
    entity_name: str = Field(description="The name or alias of the entity to get observations for"),
) -> dict[str, Any]:
    """Get observations for an entity grouped by their durability type.

    Args:
        entity_name: The name or alias of the entity to get observations for

    Returns:
        Observations grouped by durability type
    """
    try:
        result = await manager.get_observations_by_durability(entity_name)
        logger.debug("🛠️ Tool invoked: get_observations_by_durability")
        return result.model_dump()
    except Exception as e:
        raise ToolError(f"Failed to get observations: {e}")


@mcp.tool
async def delete_entry(request: DeleteEntryRequest) -> str:
    """Unified deletion tool for observations, entities, and relations. Data must be a list of the appropriate object for each entry_type:

    - entry_type = 'entity': list of entity names or aliases
    - entry_type = 'observation': [{entity_name_or_alias, [observation content]}]
    - entry_type = 'relation': [{from_entity(name or alias), to_entity(name or alias), relation_type}]

    ***CRITICAL: THIS ACTION IS DESTRUCTIVE AND IRREVERSIBLE - ENSURE THAT THE USER CONSENTS PRIOR TO EXECUTION!!!***
    """
    entry_type = request.entry_type
    data = request.data

    try:
        if entry_type == "entity":
            try:
                await manager.delete_entities(data or [])  # type: ignore[arg-type]
            except Exception as e:
                raise ToolError(f"Failed to delete entities: {e}")
            return "Entities deleted successfully"

        elif entry_type == "observation":
            await manager.delete_observations(data or [])  # type: ignore[arg-type]
            return "Observations deleted successfully"

        elif entry_type == "relation":
            await manager.delete_relations(data or [])  # type: ignore[arg-type]
            return "Relations deleted successfully"

        else:
            return ""
    except Exception as e:
        raise ToolError(f"Failed to delete entry: {e}")


@mcp.tool
async def read_graph() -> dict[str, Any]:
    """Read the entire knowledge graph.

    Returns:
        Complete knowledge graph data in JSON format
    """
    logger.debug("🛠️ Tool invoked: read_graph")
    try:
        result = await manager.read_graph()

        # Sort observations within each entity by timestamp (descending)
        def _obs_ts(obs_ts: str | None) -> datetime:
            try:
                if not obs_ts:
                    return datetime.min
                return datetime.fromisoformat(obs_ts.replace("Z", "+00:00"))
            except Exception:
                return datetime.min

        for entity in result.entities:
            entity.observations.sort(key=lambda o: _obs_ts(o.timestamp), reverse=True)

        return result.model_dump(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to read graph: {e}")


@mcp.tool
async def search_nodes(
    query: str = Field(
        description="The search query to match against entity names, aliases, types, and observation content"
    ),
) -> dict[str, Any]:
    """Search for nodes in the knowledge graph based on a query.

    Args:
        query: The search query to match against entity names, aliases, types, and/or observation content

    Returns:
        Search results containing matching nodes
    """
    try:
        result = await manager.search_nodes(query)
        logger.debug("🛠️ Tool invoked: search_nodes")
        return result.model_dump(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to search nodes: {e}")


@mcp.tool
async def open_nodes(
    entity_names: list[str] = Field(description="List of entity names or aliases to retrieve"),
) -> dict[str, Any]:
    """Open specific nodes in the knowledge graph by their names.

    Args:
        entity_names: List of entity names or aliases to retrieve

    Returns:
        Retrieved node data
    """
    try:
        result = await manager.open_nodes(entity_names)
        logger.debug("🛠️ Tool invoked: open_nodes")
        return result.model_dump(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to open nodes: {e}")


@mcp.tool
async def merge_entities(
    newentity_name: str = Field(
        description="Name of the new merged entity (must not conflict with an existing name or alias unless part of the merge)"
    ),
    entity_names: list[str] | str = Field(
        description="Names or aliases of entities to merge into the new entity"
    ),
) -> dict[str, Any]:
    """Merge a list of entities into a new entity with the provided name.

    The manager will combine observations and update relations to point to the new entity.
    """
    try:
        names: list[str] = [entity_names] if isinstance(entity_names, str) else entity_names
        merged = await manager.merge_entities(newentity_name, names)
        logger.debug("🛠️ Tool invoked: merge_entities")
        return merged.dict(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to merge entities: {e}")

@mcp.tool
async def get_email_update() -> list[EmailSummary]:
    """Get new email summaries from Supabase."""
    return await supabase.get_new_email_summaries()


#### Main application entry point ####

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
