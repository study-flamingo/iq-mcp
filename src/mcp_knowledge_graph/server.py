"""
FastMCP Server implementation for temporal knowledge graph memory.

This module implements the Model Context Protocol server that exposes
knowledge graph operations as tools for LLM integration using FastMCP 2.11.
"""

import asyncio
from fastmcp import FastMCP
from pydantic import Field
from typing import Any
from fastmcp.exceptions import ToolError, ValidationError

from .manager import KnowledgeGraphManager
from .models import (
    CreateEntryRequest,
    DeleteEntryRequest,
    AddObservationResult,
    CreateEntityResult,
    CreateRelationResult,
    CleanupResult,
    KnowledgeGraph,
    UserIdentifier,
 )
from .settings import Settings as settings, Logger as logger


import sys

try:
    from .notify import supabase, EmailSummary
except ImportError:
    logger.warning("Error starting notification module: Supabase not found - install with `uv pip install supabase`")
    supabase = None
    EmailSummary = None

# Load settings once and configure logging level accordingly


# Initialize the knowledge graph manager and FastMCP server
logger.debug(f"🔍 Memory path: {settings.memory_path}")
manager = KnowledgeGraphManager(settings.memory_path)

# Create FastMCP server instance
mcp = FastMCP(name="iq-mcp", version="0.1.0")


@mcp.tool
async def create_entry(request: CreateEntryRequest) -> str:
    """Add entities, observations, or relations to the knowledge graph.

    'data' must be a list of the appropriate object for each entry_type:

    ## Adding Entities
    'data' must be a list of Entities:
      - name: entity_name
      - entity_type: entity_type
      - observations: list of Observations
        - content: str
        - durability: Literal['temporary', 'short-term', 'long-term', 'permanent']
      - aliases: list of str (optional)
      - icon: Emoji to represent the entity (optional)

    ## Adding Observations
    'data' must be a list of Observations:
      - entity_name: entity_name
      - content: str

    ## Adding Relations
    'data' must be a list of Relations:
      - from: entity_name
      - to: entity_name
      - relation_type: relation_type

    Aliases are resolved to canonical entity names by the manager.
    """
    entry_type = request.entry_type
    data = request.data
    try:
        if entry_type == "observation":
            observation_result: list[AddObservationResult] = await manager.apply_observations(data)
            result = ""
            for r in observation_result:
                result += str(r) + "\n"

        elif entry_type == "entity":
            entity_result: CreateEntityResult = await manager.create_entities(data)
            result = str(entity_result)

        elif entry_type == "relation":
            relation_result: CreateRelationResult = await manager.create_relations(data)
            result = str(relation_result)

        else:
            raise ValueError(f"Invalid entry type: {entry_type}")

    except Exception as e:
        raise ToolError(f"Failed to create entry: {e}")
    
    return result

@mcp.tool
async def cleanup_outdated_observations() -> str:
    """Remove observations that are likely outdated based on their durability and age.

    Returns:
        Summary of cleanup operation
    """
    try:
        result = await manager.cleanup_outdated_observations()
        return str(result)
    except Exception as e:
        raise ToolError(f"Failed to cleanup observations: {e}")


@mcp.tool
async def get_observations_by_durability(
    entity_name: str = Field(description="The name or alias of the entity to get observations for"),
) -> str:
    """Get observations for an entity grouped by their durability type.

    Args:
        entity_name: The name or alias of the entity to get observations for

    Returns:
        Observations grouped by durability type
    """
    try:
        result = await manager.get_observations_by_durability(entity_name)
        return str(result)
    except Exception as e:
        raise ToolError(f"Failed to get observations: {e}")


@mcp.tool
async def delete_entry(request: DeleteEntryRequest) -> str:
    """Unified deletion tool for observations, entities, and relations. Data must be a list of the appropriate object for each entry_type:

    - 'entity': list of entity names or aliases
    - 'observation': [{entity_name_or_alias, [observation content]}]
    - 'relation': [{from_entity(name or alias), to_entity(name or alias), relation_type}]

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
async def read_graph() -> str:
    """Read the entire knowledge graph.

    Returns:
        Complete knowledge graph data in JSON format, and a boolean indicating if user info is missing
    """
    try:
        graph, user_info_missing = await manager.read_graph()

        # Sort observations within each entity by timestamp (descending)
        # def _obs_ts(obs_ts: str | None) -> datetime:
        #     try:
        #         if not obs_ts:
        #             return datetime.min
        #         return datetime.fromisoformat(obs_ts.replace("Z", "+00:00"))
        #     except Exception:
        #         return datetime.min

        # for entity in result.entities:
        #     entity.observations.sort(key=lambda o: _obs_ts(o.timestamp), reverse=True)

        # Compose a sensible display name for the user, based on available data and preferences
        entities = graph.entities
        relations = graph.relations

        # Compose a sensible display name for the user, based on available data and preferences
        if graph.user_info.preferred_name:
            preferred_name = graph.user_info.preferred_name
        if graph.user_info.nickname:
            nickname = graph.user_info.nickname
        if graph.user_info.names:
            names = graph.user_info.names
        if graph.user_info.first_name:
            first_name = graph.user_info.first_name
        if graph.user_info.last_name:
            last_name = graph.user_info.last_name
        if not preferred_name and not nickname and not names and not first_name and not last_name:
            user_name = "default_user"
            user_info_missing: bool = True
        else:
            user_name = preferred_name or nickname or names[0] or first_name or last_name

        result = "🧠 You remember the following information about the user:\n"
        result += f"**{user_name}** ({names[0]})\n"
        
        # Display entities
        result += f"\n👤 Entities: {len(graph.entities)}\n"
        for e in graph.entities:
            i = ""
            if e.icon:
                i = f"{e.icon} "
            result += f"  - {i}{e.name} ({e.entity_type})\n"
        
        # Display relations
        result += f"\n🔗 Relations: {len(graph.relations)}\n"
        for r in graph.relations:
            result += f"  - {r.from_entity} -> {r.to_entity} ({r.relation_type})\n"
        

        # Replace the default user with the user's preferred name
        for e in graph.entities:
            if "default_user" in e.name.lower():
                e.name = user_name
        
        results: list[str] = [str(display_graph)]
        if user_info_missing:
            results.append(''.join(["**ALERT**: User info is missing from the graph! Talk with the user, and ",
                                    "use the update_user_info tool to update the graph with the user's ",
                                    "identifying information."]))
        result = "\n\n".join(results)
        

        result += f"\n👤 Entities: {len(self.entities)}\n"
        for e in self.entities:
            result += f"  {str(e)}\n"
        result += f"\n🔗 Relations: {len(self.relations)}\n"
        for r in self.relations:
            result += f"  {str(r)}\n"
        result += "\n"
        return result
    
    except Exception as e:
        raise ToolError(f"Failed to read graph: {e}")

@mcp.tool
async def update_user_info(user_info: UserIdentifier) -> str:
    """
    Update the user's identifying information in the graph. This tool should be rarely called, and
    only if it appears that the user's identifying information is missing or incorrect, or if the
    user specifically requests to do so.
    
    Args:
      - preferred_name: The preferred name of the user. Preferred name is prioritized over other
        names for the user. If not provided, one will be selected from the other provided names in
        the following fallback order:
          1. Nickname
          2. Prefix + First name
          3. First name
          4. Last name
      - first_name: The given name of the user
      - middle_names: The middle names of the user
      - last_name: The family name of the user
      - pronouns: The pronouns of the user
      - nickname: The nickname of the user
      - prefixes: The prefixes of the user
      - suffixes: The suffixes of the user
      - emails: The email addresses of the user

      * One of the following MUST be provided: preferred_name, first_name, last_name, or nickname

    Returns:
        On success, the updated user info.
        On failure, an error message.

    Example user response:
        "My name is Dr. John Alexander Robert Doe Jr., M.D., AKA 'John Doe', but you can
        call me John. My pronouns are he/him. My email address is john.doe@example.com,
        but my work email is john.doe@work.com."

    From this response, you would extract the following information:
        - Preferred name: "John"
        - First name: "John"
        - Middle name(s): "Alexander", "Robert"
        - Last name: "Doe"
        - Pronouns: "he/him"
        - Nickname: "John Doe"
        - Prefixes: "Dr."
        - Suffixes: "Jr.", "M.D."
        - Email address(es): "john.doe@example.com", "john.doe@work.com"
    """
    if not user_info.preferred_name and not user_info.first_name and not user_info.nickname and not user_info.last_name:
        raise ValueError("Either a preferred name, first name, last name, or nickname are required")
    
    # Strip whitespace from all fields
    try:
        user_info.preferred_name = user_info.preferred_name.strip()
        user_info.first_name = user_info.first_name.strip()
        user_info.last_name = user_info.last_name.strip()
        user_info.middle_names = [name.strip() for name in user_info.middle_names]
        user_info.pronouns = user_info.pronouns.strip()
        user_info.nickname = user_info.nickname.strip()
        user_info.prefixes = [name.strip() for name in user_info.prefixes]
        user_info.suffixes = [name.strip() for name in user_info.suffixes]
        user_info.emails = [email.strip() for email in user_info.emails]
    except Exception as e:
        logger.warning(f"User info validation warning: {e}")

    try:
        result = await manager.update_user_info(user_info)
        return str(result)
    except Exception as e:
        raise ToolError(f"Failed to update user info: {e}")

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
        return result.model_dump(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to search nodes: {e}")


@mcp.tool
async def open_nodes(
    entity_names: list[str] = Field(description="List of entity names or aliases to retrieve"),
) -> dict[str, Any]:
    """Open specific nodes (entities) in the knowledge graph by their names.

    Args:
        entity_names: List of entity names or aliases to retrieve

    Returns:
        Retrieved node data - observations about the entity.
    """
    try:
        result = await manager.open_nodes(entity_names)
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
        return merged.dict(by_alias=True)
    except Exception as e:
        raise ToolError(f"Failed to merge entities: {e}")

@mcp.tool
async def get_email_update() -> list[EmailSummary]:
    """Get new email summaries from Supabase."""
    return await supabase.get_new_email_summaries()

if settings.debug:
    @mcp.tool
    async def DEBUG_save_graph() -> str:
        """DEBUG TOOL: Test loading, and then immediately saving the graph."""
        try:
            graph, user_info_missing = await manager._load_graph()

            if user_info_missing:
                logger.warning("DEBUG TOOL ERROR: User info is missing from the graph! This is expected if the graph is empty.")

            await manager._save_graph(graph)
        except Exception as e:
            raise ToolError(f"DEBUG TOOL ERROR: Failed to save graph: {e}")
        return "✅ Graph saved successfully!"

@mcp.tool
async def read_user_info(observations: bool = False) -> str:
    """Read the user info from the graph.
    
    Args:
      - observations: Include observations related to the user in the response."""
    try:
        graph = await manager._load_graph()
        if "default_user" in graph.user_info.preferred_name.lower():
            return "It looks like the user info hasn't been set yet! Update the user info using the update_user_info tool."
        
        if observations:
            observations = await manager.get_observations_by_entity(graph.user_info.preferred_name)
            return f"User info: {graph.user_info}\n\nObservations: {observations}"
        
        return str(graph.user_info)
    except Exception as e:
        raise ToolError(f"DEBUG TOOL ERROR: Failed to load graph: {e}")


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
        logger.error(f"🛑 Critical server error: {e}")
        sys.exit(1)


def run_sync():
    """Synchronus entry point for the server."""
    asyncio.run(start_server())

if __name__ == "__main__":
    asyncio.run(start_server())
