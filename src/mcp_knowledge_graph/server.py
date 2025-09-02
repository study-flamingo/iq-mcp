"""
FastMCP Server implementation for temporal knowledge graph memory.

This module implements the Model Context Protocol server that exposes
knowledge graph operations as tools for LLM integration using FastMCP 2.11.
"""

import asyncio
from datetime import tzinfo
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
    KnowledgeGraphException,
    UserIdentifier,
    CreateEntityRequest,
    CreateRelationRequest,
    ObservationRequest,
    Entity,
)
from .settings import Settings as settings, Logger as logger


import sys

try:
    from .supabase import supabase, EmailSummary
except Exception as e:
    logger.warning(
        "Supabase integration disabled: %s", e
    )
    supabase = None
    EmailSummary = None

# Load settings once and configure logging level accordingly


# Initialize the knowledge graph manager and FastMCP server
manager = KnowledgeGraphManager(settings.memory_path)

# Create FastMCP server instance
mcp = FastMCP(name="iq-mcp", version="1.0.0")


#### Helper functions ####
def _print_user_info(
    graph: KnowledgeGraph, include_observations: bool = False, include_relations: bool = False
):
    """Get the user's info from the knowledge graph and print to a string.

    Args:
      - include_observations: Include observations related to the user in the response.
      - include_relations: Include relations related to the user in the response.
    """
    logger.setLevel("DEBUG")
    try:
        # Compose a sensible display name for the user, based on available data and preferences
        last_name = graph.user_info.last_name or ""
        first_name = graph.user_info.first_name or ""
        nickname = graph.user_info.nickname or ""
        names = graph.user_info.names or []
        preferred_name = graph.user_info.preferred_name or ""
        # timezone = graph.user_info.timezone or "UTC"
        linked_entity = graph.user_info.linked_entity or None

        if linked_entity:
            user_name = linked_entity.name
        else:
            logger.warning(
                f"No linked entity found for user {graph.user_info.preferred_name}, using fallback names"
            )
            user_name = last_name or ""
            user_name = first_name or ""
            user_name = names[0] or ""
            user_name = nickname or ""
            user_name = preferred_name or ""
            # user_info_unlinked = True

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
        result = (
            "" if settings.no_emojis else "🧠 "
        ) + "You remember the following information about the user:\n"
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
            from_entity, to_entity = manager.get_entities_from_relation(graph.user_info.linked_entity)
            result += ("\n" if settings.no_emojis else "\n🔍 ") + "Observations (times in UTC):\n"
            for o in from_entity.observations:
                ts = o.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                result += f"  - {o.content} ({ts}, {o.durability.value})\n"
    except Exception as e:
        logger.error(f"Failed to print observations: {e} - trying deprecated method")

        # soon-to-be-deprecated process if user_info isn't linked yet
        try:
            if include_observations:
                lookup_result: KnowledgeGraph = manager.open_nodes(
                    "__default_user__"
                ) or manager.open_nodes("default_user")
                if not lookup_result.entities:
                    logger.warning("No entities found for names: __default_user__ or default_user")
                    return result
                user_entity = lookup_result.entities[0]
                result += ("\n" if settings.no_emojis else "\n🔍 ") + "Observations (times in UTC):\n"
                for o in user_entity.observations:
                    ts = o.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    result += f"  - {o.content} ({ts}, {o.durability.value})\n"
        except Exception as e:
            raise ToolError(f"Failed to print observations: {e}")

    # Print relations
    try:
        if include_relations:
            from_entity, to_entity = manager.get_entities_from_relation(graph.user_info.linked_entity)
            result += ("\n" if settings.no_emojis else "\n🔗 ") + "Relations:\n"
            for r in from_entity.relations:
                result += f"  - {r.from_entity} {r.relation} {r.to_entity}\n"
    except Exception as e:
        logger.error(f"Failed to print relations: {e} - trying deprecated method")
        # Deprecated fallback method
        try:
            if include_relations:
                user_entity = manager.open_nodes("__default_user__") or manager.open_nodes("default_user")
                result += ("\n" if settings.no_emojis else "\n🔗 ") + "Relations:\n"
                for r in user_entity.relations:
                    result += f"  - {r.from_entity} {r.relation} {r.to_entity}\n"
        except Exception as e:
            raise ToolError(f"Failed to print relations: {e}")

    return result

async def _print_relations_from_graph(
    graph: KnowledgeGraph = None,
    entities_list: list[Entity] = None,
    prefix: str = "  - ",
    separator: str = "\n  - ", 
    suffix: str = "\n",
    md_links: bool = True,
    include_ids: bool = True,
    include_types: bool = True,
    ):
    """
    Print relations in a readable format. Respects the no_emojis property from Settings.
    A number of options are available to customize the display. All options are optional, and the 
    default values are used if not specified.
    
    May also pass a list of entities to print relations from instead of the graph.
    
    Format: <from_entity> <relation> <to_entity><separator>
    
    One of the following args is required:

        - graph: The knowledge graph to print relations from. Typical usage.
        - entities_list: A list of entities to print relations from.
    
    Optional Args:

        - separator: The separator to use between relations. Default is ` \n  - `.
        - md_links: Whether to use Markdown links for the entities. Default is True.
        - prefix: The prefix to use before the relations. Default is `  - `.
        - suffix: The suffix to use after the relations. Default is `\n`.
        - include_ids: Whether to include the IDs of the entities in the display. Default is True.
        - include_types: Whether to include the types of the entities in the display. Default is True.
    
    Example of default list display:
    ```
      - [👤 John Doe](123) (person) is a friend of [👤 Jane Doe](456) (person)
      - [👤 Jim Doe](789) (person) is an enemy of [👤 Janet Doe](012) (person)
    (trailing newline)
    ```
    """
    if graph:
        entities_list = entities_list or graph.entities
    else:
        entities_list = entities_list or None
        
    if not entities_list:
        raise ValueError("No entities list provided and no graph provided to get entities from")
    
    result = prefix
    entity_map = await manager._get_entity_id_map(entities_list=entities_list)
    try:
        for r in graph.relations:
            items = []
            try:
                a = entity_map.get(r.from_id)
                b = entity_map.get(r.to_id)
                
                # If this is the user-linked entity, use the preferred name instead; if name is missing, use "unknown"
                a_name = "unknown"
                b_name = "unknown"
                if a:
                    if a.name == "__user__" or a.name.lower().strip() == "user":
                        a_name = graph.user_info.preferred_name
                    else:
                        a_name = a.name if a.name else "unknown"
                if b:
                    if b.name == "__user__" or b.name.lower().strip() == "user":
                        b_name = graph.user_info.preferred_name
                    else:
                        b_name = b.name if b.name else "unknown"
            except Exception as e:
                raise ToolError(f"Failed to get relation entities: {e}")

            # Compose strings
            if md_links:
                link_from = f"[{a.icon}{a_name}]({a.id})" if a else f"{a_name}"
                link_to = f"[{b.icon}{b_name}]({b.id})" if b else f"{b_name}"
            else:
                link_from = f"{a.icon}{a_name}" if a else f"{a_name}"
                link_to = f"{b.icon}{b_name}" if b else f"{b_name}"
            if include_ids:
                link_from += f" (ID: {a.id})" if a else ""
                link_to += f" (ID: {b.id})" if b else ""
            if include_types:
                link_from += f" ({a.entity_type})" if a else ""
                link_to += f" ({b.entity_type})" if b else ""
            
            # Add to result
            items.append(f"{link_from} {r.relation} {link_to}")

        # Join items with the separator
        result += separator.join(items)

        # Finally, add the suffix
        result += suffix

        return result
    except Exception as e:
        raise ToolError(f"Failed to print relations: {e}")


@mcp.tool
async def read_graph():
    """Read the entire knowledge graph.

    Returns:
        Complete knowledge graph data in JSON format, and a boolean indicating if user info is missing
    """
    try:
        graph = await manager.read_graph()

        result = _print_user_info(graph)
        try:
            user_name = graph.user_info.preferred_name  # Preferred name should be set during entity creations at minimum
        except Exception as e:
            logger.error(f"Failed to print user info: {e}")

        # Print all entities
        try:
            result += f"\n👤 You've made observations about {len(graph.entities)} entities:\n"
            for e in graph.entities:
                i = e.icon
                if e.icon:
                    i = f"{e.icon} "
                if "default_user" in e.name.lower():
                    entity_name = user_name
                else:
                    entity_name = e.name
                result += f"  - {i}{entity_name} ({e.entity_type})\n"
        except Exception as e:
            logger.error(f"Failed to print entities: {e}")

        # Print all relations
        try:
            result += (
                f"\n🔗 You've learned about {len(graph.relations)} relations between these entities:\n"
            )
            obs_result = await _print_relations_from_graph(graph)
            if obs_result:
                result += obs_result
            else:
                raise KnowledgeGraphException(f"No output from _print_relations_from_graph: {e}")
        except KnowledgeGraphException as e:
            result += (f"\nERROR: Failed to print relations: {e}")
        except Exception as e:
            raise ToolError(f"Error while printing relations: {e}")
        return result

    except RuntimeError as e:
        raise RuntimeError(f"Critical error while printing graph: {e}")
    except Exception as e:
        raise ToolError(f"Error while printing graph: {e}")


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
async def create_entities(new_entities: list[CreateEntityRequest]):
    """
    Add new entities (nodes) to the knowledge graph.
    
    ## Adding Entities
    'data' must be a list of Entities:
      - name: entity_name (required)
      - entity_type: entity_type (required)
      - observations: list of observations (optional)
        - content: str (required)
        - durability: Literal['temporary', 'short-term', 'long-term', 'permanent'] (optional, defaults to 'short-term')
      - aliases: list of str (optional)
      - icon: Emoji to represent the entity (optional)
    """
    try:
        result = await manager.create_entities(new_entities)
        entities = result.entities or None
        if not entities or len(entities) == 0:
            return "No new entities created!"
        elif len(entities) == 1:
            result = "Entity created successfully:\n"
        else:
            result = f"{len(entities)} entities created successfully:\n"

        for e in entities:
            i = f"{e.icon} " if e.icon and not settings.no_emojis else ""
            result += f"{i}**{e.name}** ({e.entity_type})\n"
            if e.aliases:
                result += "  Alias(es): "
                alias_list = []
                for a in e.aliases:
                    alias_list.append(a)
                result += f"{', '.join(alias_list)}\n"
            if e.observations:
                result += "  Observation(s): "
                for o in e.observations:
                    result += f"  - {o.content} ({o.durability.value})\n"
            result += "\n"
        
        return result
    except Exception as e:
        raise ToolError(f"Failed to create entities: {e}")

@mcp.tool
async def create_relations(new_relations: list[CreateRelationRequest]):
    """
    Record relations (edges) between entities in the knowledge graph.
    
    Args:

      - new_relations: list of CreateRelationRequest objects

        Each relation must be a CreateRelationRequest object with the following properties:
        
        - from (str): Origin entity name
        - to (str): Destination entity name
        - relation (str): Relation type

    Relations must be in active voice, directional, and should be concise and to the point. 
    Relation content must exclude the 'from' and 'to' entities, and be lowercase. Examples:
    
      - <from_entity> "grew up during" <to_entity> (relation = "grew_up_during")
      - <from_entity> "was a sandwich artist for 20 years at" <to_entity>
      - <from_entity> "is going down a rabbit hole researching" <to_entity>
      - <from_entity> "once went on a road trip with" <to_entity>
      - <from_entity> "needs to send weekly reports to" <to_entity>

    Note: a relation with content "is" will result in adding an alias to the 'from' entity. Prefer
    using the add_alias tool instead.
    """
    try:
        result = await manager.create_relations(new_relations)
        relations = result.relations or None
        if not relations or len(relations) == 0:
            return "No new relations created!"
        elif len(relations) == 1:
            result = "Relation created successfully:\n"
        else:
            result = f"{len(relations)} relations created successfully:\n"

        for r in relations:
            # Resolve print elements from entity objects
            f = r.from_entity
            t = r.to_entity
            f_i = f"{f.icon} " if f.icon and not settings.no_emojis else ""
            t_i = f"{t.icon} " if t.icon and not settings.no_emojis else ""
            result += f"{f_i}{f.name} ({f.entity_type}) {r.relation} {t_i}{t.name} ({t.entity_type})\n"

        return result
    except Exception as e:
        raise ToolError(f"Failed to create relations: {e}")

@mcp.tool
async def add_observations(new_observations: list[ObservationRequest]):
    """
    Add observations about entities or the user (via the user-linked entity) to the knowledge graph.

    Args:
      - new_observations: list of ObservationRequest objects

    Each observation must be a ObservationRequest object with the following properties:

      - entity_name (str): Entity name (optional, deprecated)
      - entity_id (str): Entity id (required), or 'user' for the user-linked entity
      - content (str): Observation content (required)
      - durability (Literal['temporary', 'short-term', 'long-term', 'permanent']): Durability of the observation (optional, defaults to 'short-term')

    Either entity_name or entity_id must be provided. 'entity_name' is deprecated and will be removed in a future version.

    Observation content must be lowercase, in active voice, exclude the 'from' entity, and concise. Examples:

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

    Observations added to non-existent entities will result in the creation of the entity.
    """
    try:
        result = await manager.add_observations(new_observations)
        return result
    except Exception as e:
        raise ToolError(f"Failed to add observations: {e}")

@mcp.tool
async def cleanup_outdated_observations():
    """Remove observations that are likely outdated based on their durability and age.

    Returns:
        Summary of cleanup operation
    """
    try:
        cleanup_result = await manager.cleanup_outdated_observations()
        ent = cleanup_result.entities_processed_count
        obs = cleanup_result.observations_removed_count
        obs_detail = cleanup_result.removed_observations
        result = (
            "" if settings.no_emojis else "🧹 "
        ) + f"Cleaned up {obs} observations from {ent} entities"
        logger.info(result)
        logger.debug(f"Removed observations: {obs_detail}")
        return result
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
    - 'relation': [{from_entity(name or alias), to_entity(name or alias), relation}]

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
):
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
    """
    Open specific nodes (entities) in the knowledge graph by their names or aliases.

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
                result_str += f"  - {r.from_entity} {r.relation} {r.to_entity}\n"
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
):
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
async def get_email_update():
    """Get new email summaries from Supabase."""
    if supabase is None or not getattr(supabase, "enabled", False):
        return "Supabase integration is not configured."
    try:
        response = await supabase.get_new_email_summaries()
        if not response:
            return "No new email summaries found!"
        result = ""
        for summary in response:
            result += f"Messsage ID: {summary.id}\n"
            result += f"From: {summary.from_address} ({summary.from_name})\n"
            result += f"Reply-To: {summary.reply_to}\n"
            result += f"Timestamp: {summary.timestamp}\n"
            result += f"Subject: {summary.subject}\n"
            result += f"Summary: {summary.summary}\n"
            try:
                links_list = summary.links or []
                links_str = "\n- ".join([str(link.get("url", link)) for link in links_list])
                if links_str:
                    result += f"Links: {links_str}"
            except Exception:
                pass
            result += "\n\n"
        return result
    except Exception as e:
        raise ToolError(f"Failed to get email updates: {e}")

if settings.debug:
    @mcp.tool
    async def DEPRECATED_create_entry(request: CreateEntryRequest):
        """Add entities, observations, or relations to the knowledge graph.

        'data' must be a list of the appropriate object for each entry_type:


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

        """
        logger.warning("This tool is deprecated and will be removed in a future version. Use the create_entities, create_relations, and apply_observations tools instead.")

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
