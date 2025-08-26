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
    logger.warning(
        "Error starting notification module: Supabase not found - install with `uv pip install supabase`"
    )
    supabase = None
    EmailSummary = None

# Load settings once and configure logging level accordingly


# Initialize the knowledge graph manager and FastMCP server
logger.debug(f"🔍 Memory path: {settings.memory_path}")
manager = KnowledgeGraphManager(settings.memory_path)

# Create FastMCP server instance
mcp = FastMCP(name="iq-mcp", version="0.1.0")


#### Helper functions ####
async def _print_user_info(
    graph: KnowledgeGraph, include_observations: bool = False, include_relations: bool = False
) -> str:
    """Get the user's info from the knowledge graph and print to a string.

    Args:
      - include_observations: Include observations related to the user in the response.
      - include_relations: Include relations related to the user in the response.
    """
    try:
        # Compose a sensible display name for the user, based on available data and preferences
        last_name = graph.user_info.last_name or ""
        first_name = graph.user_info.first_name or ""
        nickname = graph.user_info.nickname or ""
        names = graph.user_info.names or []
        preferred_name = graph.user_info.preferred_name or ""

        user_name = last_name or ""
        user_name = first_name or ""
        user_name = names[0] or ""
        user_name = nickname or ""
        user_name = preferred_name or ""

        # Ensure that the user's name is set
        user_info_missing: bool = False
        if not user_name:
            raise ValueError(
                "Some weird error happened when trying to determine the user's name, fix me!"
            )
        elif "default_user" in user_name.lower():
            user_info_missing = True

        middle_names = graph.user_info.middle_names or []
        pronouns = graph.user_info.pronouns or ""
        emails = graph.user_info.emails or []
        prefixes = graph.user_info.prefixes or []
        suffixes = graph.user_info.suffixes or []
    except Exception as e:
        raise ToolError(f"Failed to load user info: {e}")

    try:
        # Start with printing the user's info
        result = "🧠 You remember the following information about the user:\n"
        result += f"**{user_name}** ({names[0]})\n"
        if middle_names:
            result += f"Middle name(s): {', '.join(middle_names)}\n"
        if nickname and nickname != user_name:
            result += f"Nickname: {nickname}\n"
        if pronouns:
            result += f"Pronouns: {pronouns}\n"
        if emails:
            result += f"Email addresses: {', '.join(emails)}\n"
        if prefixes:
            result += f"Prefixes: {', '.join(prefixes)}\n"
        if suffixes:
            result += f"Suffixes: {', '.join(suffixes)}\n"
        if names[1:]:
            result += "May also go by:\n"
            for name in names[1:]:
                result += f"  - {name}\n"

        # If it looks like the default/dummy user info is still present, prompt the LLM to update the user's info
        if user_info_missing:
            info_missing_msg = "".join(
                [
                    "\n**ALERT**: User info is missing from the graph! Talk with the user, and ",
                    "use the update_user_info tool to update the graph with the user's ",
                    "identifying information.\n",
                ]
            )
            result += info_missing_msg
    except Exception as e:
        raise ToolError(f"Failed to print user info: {e}")

    # Print observations
    try:
        if include_observations:
            lookup_result: KnowledgeGraph = await manager.open_nodes(
                "__default_user__"
            ) or await manager.open_nodes("default_user")
            user_entity = lookup_result.entities[0]
            result += "\n🔍 Observations:\n"
            for o in user_entity.observations:
                result += f"  - {o.content} ({str(o.timestamp)}, {str(o.durability)})\n"
    except Exception as e:
        raise ToolError(f"Failed to print observations: {e}")

    # Print relations
    try:
        if include_relations:
            user_entity = await manager.open_nodes("__default_user__")
            result += "\n🔗 Relations:\n"
            for r in user_entity.relations:
                result += f"  - {r.from_entity} {r.relation_type} {r.to_entity}\n"
    except Exception as e:
        raise ToolError(f"Failed to print relations: {e}")

    return result


@mcp.tool
async def read_graph():
    """Read the entire knowledge graph.

    Returns:
        Complete knowledge graph data in JSON format, and a boolean indicating if user info is missing
    """
    try:
        graph = await manager.read_graph()

        result = await _print_user_info(graph)
        user_name = (
            graph.user_info.preferred_name
            or graph.user_info.first_name
            or graph.user_info.last_name
            or graph.user_info.nickname
            or ""
        )

        # Print all entities
        result += f"\n👤 You've made observations about {len(graph.entities)} entities:\n"
        for e in graph.entities:
            i = ""
            if e.icon:
                i = f"{e.icon} "
            if "default_user" in e.name.lower():
                entity_name = user_name
            else:
                entity_name = e.name
            result += f"  - {i}{entity_name} ({e.entity_type})\n"

        # Print all relations
        result += (
            f"\n🔗 You've learned about {len(graph.relations)} relations between these entities:\n"
        )
        for r in graph.relations:
            if "default_user" in r.from_entity.lower():
                from_entity = user_name
            else:
                from_entity = r.from_entity
            if "default_user" in r.to_entity.lower():
                to_entity = user_name
            else:
                to_entity = r.to_entity
            result += f"  - {from_entity} {r.relation_type} {to_entity}\n"

        return result

    except Exception as e:
        raise ToolError(f"Failed to read graph: {e}")


@mcp.tool
async def read_user_info(include_observations: bool = False, include_relations: bool = False):
    """Read the user info from the graph.

    Args:
      - include_observations: Include observations related to the user in the response.
      - include_relations: Include relations related to the user in the response.
    """
    try:
        graph = await manager.read_graph()
        if "default_user" in graph.user_info.model_dump().values():
            return "It looks like the user info hasn't been set yet! Update the user info using the update_user_info tool."

        result_str = await _print_user_info(graph, include_observations, include_relations)
        return result_str
    except Exception as e:
        raise ToolError(f"Failed to read user info: {e}")


@mcp.tool
async def create_entry(request: CreateEntryRequest):
    """Add entities, observations, or relations to the knowledge graph.

    'data' must be a list of the appropriate object for each entry_type:

    ## Adding Entities
    'data' must be a list of Entities:
      - name: entity_name (required)
      - entity_type: entity_type (required)
      - observations: list of observations (required)
        - content: str (required)
        - durability: Literal['temporary', 'short-term', 'long-term', 'permanent'] (optional, defaults to 'short-term')
      - aliases: list of str (optional)
      - icon: Emoji to represent the entity (optional)

    An entity should be created with at least one observation.

    ## Adding Observations
    'data' must be a list of observations:
      - entity_name: entity_name (required)
      - content: str (required)
      - durability: Literal['temporary', 'short-term', 'long-term', 'permanent'] (optional, defaults to 'short-term')

    Observation content must be in active voice, excule the 'from' entity, lowercase, and should be concise and to the point. Examples:
      - "likes chicken"
      - "enjoys long walks on the beach"
      - "can ride a bike with no handlebars"
      - "wants to be a movie star"
      - "dropped out of college to pursue a career in underwater basket weaving"

    Durability determines how long the observation is kept in the knowledge graph and should reflect
    the expected amount of time the observation is relevant.
      - 'temporary': The observation is only relevant for a short period of time (1 month)
      - 'short-term': The observation is relevant for a few months (3 months).
      - 'long-term': The observation is relevant for a few months to a year. (1 year)
      - 'permanent': The observation is relevant for a very long time, or indefinitely. (never expires)

    ## Adding Relations
    'data' must be a list of relations:
      - from: entity_name
      - to: entity_name
      - relation_type: relation_type

    Relations must be in active voice, directional, and should be concise and to the point. Examples:
      - <from_entity> "grew up during" <to_entity>
      - <from_entity> "was a sandwich artist for 20 years at" <to_entity>
      - <from_entity> "is going down a rabbit hole researching" <to_entity>
      - <from_entity> "once went on a road trip with" <to_entity>
      - <from_entity> "needs to send weekly reports to" <to_entity>
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
async def update_user_info(user_info: UserIdentifier) -> str:
    """
    Update the user's identifying information in the graph. This tool should be rarely called, and
    only if it appears that the user's identifying information is missing or incorrect, or if the
    user specifically requests to do so.

    Args:
      - preferred_name: The preferred name of the user. (required)
        Preferred name is prioritized over other names for the user. If not provided, one will be
        selected from the other provided names in the following fallback order:
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
    if (
        not user_info.preferred_name
        and not user_info.first_name
        and not user_info.nickname
        and not user_info.last_name
    ):
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
        return result.model_dump()
    except Exception as e:
        raise ToolError(f"Failed to search nodes: {e}")


@mcp.tool
async def open_nodes(
    entity_names: list[str] = Field(description="List of entity names or aliases to retrieve"),
):
    """Open specific nodes (entities) in the knowledge graph by their names.

    Args:
        entity_names: List of entity names or aliases to retrieve

    Returns:
        Retrieved node data - observations about the entity.
    """
    try:
        result = await manager.open_nodes(entity_names)

        # Print the result
        result_str = ""
        for e in result.entities:
            result_str += f"Entity: {e.name} ({e.entity_type})\n"
            result_str += "Observations:\n"
            for o in e.observations:
                result_str += f"  - {o.content} ({str(o.timestamp)}, {str(o.durability)})\n"
            for r in e.relations:
                result_str += f"  - {r.from_entity} {r.relation_type} {r.to_entity}\n"
        return result_str
    except Exception as e:
        raise ToolError(f"Failed to open nodes: {e}")


@mcp.tool
async def merge_entities(
    new_entity_name: str = Field(
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
        merged = await manager.merge_entities(new_entity_name, names)
        return merged.model_dump()
    except Exception as e:
        raise ToolError(f"Failed to merge entities: {e}")


@mcp.tool
async def get_email_update() -> list[EmailSummary]:
    """Get new email summaries from Supabase."""
    try:
        response = await supabase.get_new_email_summaries()
        if not response:
            return "No new email summaries found!"
        else:
            result = ""
            for summary in response:
                result += f"Messsage ID: {summary.id}\n"
                result += f"From: {summary.from_address} ({summary.from_name})\n"
                result += f"Reply-To: {summary.reply_to}\n"
                result += f"Timestamp: {summary.timestamp}\n"
                result += f"Subject: {summary.subject}\n"
                result += f"Summary: {summary.summary}\n"
                result += f"Links: {'\n- '.join([link['url'] for link in summary.links])}"
                result += "\n\n"
            return result
    except Exception as e:
        raise ToolError(f"Failed to get email updates: {e}")


if settings.debug:

    @mcp.tool
    async def DEBUG_save_graph() -> str:
        """DEBUG TOOL: Test loading, and then immediately saving the graph."""
        try:
            graph = await manager._load_graph()
            await manager._save_graph(graph)
        except Exception as e:
            raise ToolError(f"DEBUG TOOL ERROR: Failed to save graph: {e}")
        return "✅ Graph saved successfully!"


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
