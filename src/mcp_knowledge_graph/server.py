"""
FastMCP Server implementation for temporal knowledge graph memory.

This module implements the Model Context Protocol server that exposes
knowledge graph operations as tools for LLM integration using FastMCP 2.11.
"""

import asyncio
import json
from datetime import tzinfo
from fastmcp import FastMCP
from pydantic import Field
from pydantic.dataclasses import dataclass
from typing import Any
from fastmcp.exceptions import ToolError, ValidationError

from .manager import KnowledgeGraphManager
from .models import (
    DeleteEntryRequest,
    EntityID,
    KnowledgeGraph,
    KnowledgeGraphException,
    Relation,
    UserIdentifier,
    CreateEntityRequest,
    CreateRelationRequest,
    ObservationRequest,
    Entity,
    CreateEntityResult,
)
from .settings import Settings as settings, Logger as logger


import sys

try:
    from .supabase import supabase, EmailSummary
except Exception as e:
    logger.warning("Supabase integration disabled: %s", e)
    supabase = None
    EmailSummary = None

# Load settings once and configure logging level accordingly


# Initialize the knowledge graph manager and FastMCP server
manager = KnowledgeGraphManager(settings.memory_path)

# Create FastMCP server instance
mcp = FastMCP(name="iq-mcp", version="1.1.0")


@dataclass
class PrintOptions:
    """
    Options for printing things such as entities, relations, or observations from the knowledge graph.
    All options are optional, and the default values are used if not specified.

    Parameters:

    - exclude_user: Whether to exclude the user from the entity list. Default is `True`.
    - prologue: A string added before the entity list. Default is `None`.
    - separator: The separator to use between list items (entities). Default is `\\n`.
    - epilogue: A string added after the entity list. Default is `\\n`.
    - md_links: Whether to use markdown-style links for the entities. Default is `True`.
    - include_ids: Whether to include the IDs of the entities in the display. Default is `True`.
    - include_types: Whether to include the types of the entities in the display. Default is `True`.
    - include_observations: Whether to include observations of the entities in the display. Default is `False`.
    - include_relations: Whether to include relations of the entities in the display. Default is `False`.
    - indent: The number of spaces to indent the entity display. Default is `2`.
    - ul: Whether to use a bulleted list. Default is `True`.
    - ol: Whether to use a numbered list. Default is `False`.
    - bullet: The bullet to use for the unordered list. Default is `-`.
    - ordinal_separator: The separator to use between the ordinal and the entity. Default is `.`

    Notes:

    - `prologue` and `epilogue` strings should include newlines, unless inline display is desired
    - `bullet` and `ordinal` are mutually exclusive
    - `include_observations` and `include_relations` will select for items that are linked to the entity in question
    - If a newline is not included in the `separator`, the list will print inline
    - If both `md_links` and `include_ids` are `True`, the link will be the ID string e.g.: `[👤 John Doe](12345678)`
    - If both `ul` and `ol` are `True` for some reason, an unordered list will be preferred
    - `indent` is applied only to the entity list, not the prologue or epilogue
    """

    exclude_user: bool = True
    prologue: str = ""
    separator: str = "\n"
    epilogue: str = "\n\n"
    md_links: bool = True
    include_ids: bool = True
    include_types: bool = True
    include_observations: bool = False
    include_relations: bool = False
    indent: int = 0
    ul: bool = True
    ol: bool = False
    bullet: str = "-"
    ordinal_separator: str = "."


#### Helper functions ####
async def print_user_info(
    graph: KnowledgeGraph | None = None, include_observations: bool = False, include_relations: bool = False, options: PrintOptions = PrintOptions()
):
    """Get the user's info from the provided knowledge graph (or the default graph from the manager) and print to a string.

    Args:
      - graph: The knowledge graph to print user info from. Will load default graph from manager if not provided.
      - include_observations: Include observations related to the user in the response.
      - include_relations: Include relations related to the user in the response.
      - options: The options to use for printing the user info. If not provided, default values will be used.
    """
    
    if graph is None:
        graph = await manager.read_graph()
    entity_id_map = await manager.get_entity_id_map(graph)
    
    # Resolve options
    prologue = options.prologue
    separator = options.separator
    indent = options.indent
    ul = options.ul
    ol = False if ul else options.ol
    bullet = options.bullet
    ordinal_separator = options.ordinal_separator
    
    ind = " " * indent if indent > 0 else ""
    os = ordinal_separator
    ord = "" if ol else bullet
    
    try:
        # Compose a sensible display name for the user, based on available data and preferences
        last_name = graph.user_info.last_name or ""
        first_name = graph.user_info.first_name or ""
        nickname = graph.user_info.nickname or ""
        preferred_name = graph.user_info.preferred_name or (
            nickname or first_name or last_name or "user"
        )
        linked_entity_id = graph.user_info.linked_entity_id or None
        middle_names = graph.user_info.middle_names or []
        pronouns = graph.user_info.pronouns or ""
        emails = graph.user_info.emails or []
        prefixes = graph.user_info.prefixes or []
        suffixes = graph.user_info.suffixes or []
        names = graph.user_info.names or [preferred_name]
    except Exception as e:
        raise ToolError(f"Failed to load user info: {e}")

    linked_entity = None
    if linked_entity_id:
        linked_entity = entity_id_map.get(linked_entity_id, None)
    if not linked_entity:
        logger.error("User-linked entity not found; proceeding without observations section")

    result = prologue
    try:
        # Start with printing the user's info
        result += f"**{preferred_name}** ({names[0]})\n"
        if middle_names:
            result += f"Middle name(s): {', '.join(middle_names)}\n"
        if nickname and nickname != preferred_name:
            result += f"Nickname: {nickname}\n"
        if pronouns:
            result += f"Pronouns: {pronouns}\n"
        if prefixes:
            result += f"Prefixes: {', '.join(prefixes)}\n"
        if suffixes:
            result += f"Suffixes: {', '.join(suffixes)}\n"
        if names[1:]:
            result += "May also go by:\n"
            for name in names[1:]:
                result += f"{ind}{ord}{os} {name}\n"
        if emails:
            result += f"Email addresses: {', '.join(emails)}\n"

    except Exception as e:
        raise ToolError(f"Failed to print user info: {e}")

    # Print observations about the user (from the user-linked entity)
    try:
        if include_observations and linked_entity:
            if len(linked_entity.observations) > 0:
                result += (
                    "\n" if settings.no_emojis else "\n🔍 "
                ) + "Observations (times in UTC):\n"
                for o in linked_entity.observations:
                    ts = o.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                    result +=   f"{ind}{ord}{os} {o.content} ({ts}, {o.durability.value}{separator}"
            else:
                pass  # No observations found in user-linked entity
    except Exception as e:
        raise ToolError(f"Failed to print user observations: {e}")

    # Print relations about the user (dynamic, from graph relations)
    try:
        if include_relations:
            for r in graph.relations:
                # skip if either entity is not found or not the user-linked entity
                a: Entity | None = entity_id_map.get(r.from_id, None)
                b: Entity | None = entity_id_map.get(r.to_id, None)
                if not a or not b:
                    logger.error(f"Failed to get entities from relation: {str(r)[:20]}...")
                    continue
                elif linked_entity_id not in [a.id, b.id]:
                    logger.debug(f"User-linked entity not found in relation {str(r)[:20]} - skipping")
                    continue
                
                # replace the user-linked entity name with the user's preferred name
                if linked_entity_id == a.id:
                    from_record = f"{preferred_name} (user)"
                else:
                    from_record = f"{a.icon_()}{a.name} ({a.entity_type})"
                if linked_entity_id == b.id:
                    to_record = f"{preferred_name} (user)"
                else:
                    to_record = f"{b.icon_()}{b.name} ({b.entity_type})"

                result += f"  - {from_record} {r.relation} {to_record}\n"

        return result
    except Exception as e:
        raise ToolError(f"Failed to print user relations: {e}")


async def print_entities(graph: KnowledgeGraph | None = None, entities: list[Entity] | None = None, options: PrintOptions = PrintOptions()):
    """
    Print entities data from a list of entities in a readable format.

    Various options are available to customize the display. All options are optional, and the
    default values are used if not specified.

    Args:

    - graph: The knowledge graph to print entities from. Required if entities is not provided.
    - entities: The list of entities to print. Required if graph is not provided.
    - options: The options to use for printing the entities. If not provided, default values will be used.

    Display format:

    ```
    <prefix><indent><bullet/ordinal><ordinal_separator> <entity><separator>...<suffix> (<entity_type>)
    ```

    Example with default values:

    ```
    <prologue empty>
      - [👤 John Doe](12345678) (person)
      - [👤 Jane Doe](87654321) (person)
      ...
    <epilogue is double newline>
    ```

    Notes:

        - `prologue` and `epilogue` strings should include newlines, unless inline display is desired
        - `bullet` and `ordinal` are mutually exclusive
        - `include_observations` and `include_relations` will select for items that are linked to the entity in question
        - If a newline is not included in the `separator`, the list will print inline
        - If both `md_links` and `include_ids` are `True`, the link will be the ID string e.g.: `[👤 John Doe](12345678)`
        - If both `ul` and `ol` are `True` for some reason, an unordered list will be preferred
        - `indent` is applied only to the entity list, not the prologue or epilogue
    """

    if not graph:
        graph = await manager.read_graph()
    if not entities:
        entities = graph.entities

    exclude_user = options.exclude_user
    prologue = options.prologue
    separator = options.separator
    epilogue = options.epilogue
    md_links = options.md_links
    include_ids = options.include_ids
    include_types = options.include_types
    indent = options.indent
    ul = options.ul
    ol = False if ul else options.ol
    bullet = options.bullet
    ordinal_separator = options.ordinal_separator

    result = ""

    # Resolve options
    ind = " " * indent if indent > 0 else ""
    os = ordinal_separator
    ord = "" if ol else bullet

    # Start rendering
    result = prologue
    try:
        i = 1
        os = ordinal_separator if ol else ""
        for e in entities:
            if (
                exclude_user
                and e.name.lower().strip() == "__user__"
                or e.name.lower().strip() == "user"
            ):
                logger.debug("User-linked entity found during entity printing, skipping")
                continue
            id = e.id
            icon = e.icon_()
            name = e.name
            type = e.entity_type
            ord = str(i) if ol else bullet

            # Compose pre-entity string (list stuff like indentation, bullet, ordinal, etc.)
            # Special case: if both ul and ol are False, omit pre-entity string
            if not ul and not ol:
                display_pre = ""
            else:
                display_pre: str = f"{ind}{ord}{os} "

            # Compose entity string (entity icon, name, id, type)
            display = ""
            if md_links and include_ids:
                display += f"[{icon}{name}]({id})"
            elif md_links and not include_ids:
                # TODO: figure out more uses for md links here
                display += f"{icon}{name}"
            elif not md_links and include_ids:
                display += f"{icon}{name} ({id})"
            elif not md_links and not include_ids:
                display += f"{icon}{name}"
            if include_types:
                display += f" ({type})"

            # Compose post-entity string (separator)
            display_post = f"{separator}"

            result += f"{display_pre}{display}{display_post}"
            i += 1

        # Finally, add the epilogue
        result += epilogue

        return result
    except Exception as e:
        raise ToolError(f"Failed to print entities: {e}")


async def print_relations(
    graph: KnowledgeGraph | None = None,
    relations: list[Relation] | None = None,
    options: PrintOptions = PrintOptions(),
) -> str:
    """
    Print relations from the graph in a readable format. Resolves entity IDs to names wherever possible.

    Args:

    - graph: The knowledge graph to print relations from. Required if relations is not provided.
    - relations: The list of relations to print. Required.
    - options: The options to use for printing the relations. If not provided, default values will be used.

    Display format:

    ```
    <prefix><indent><bullet/ordinal><ordinal_separator> <from_entity><relation><to_entity><separator>...<suffix> (<entity_type>)
    ```

    Example with default values:

    ```
    <prologue empty>
      - [👤 John Doe](12345678) is related to[👤 Jane Doe](87654321) (person)
      ...
    <epilogue is double newline>
    ```
    """
    if not graph:
        graph = await manager.read_graph()
    if not relations:
        relations = graph.relations
    entity_id_map = await manager.get_entity_id_map(graph)
    user_info = graph.user_info

    prologue = options.prologue
    epilogue = options.epilogue
    md_links = options.md_links
    include_ids = options.include_ids
    include_types = options.include_types
    indent = options.indent
    ul = options.ul
    ol = False if ul else options.ol
    bullet = options.bullet
    os = options.ordinal_separator
    separator = options.separator

    result = prologue

    # Resolve options
    i = 1  # for ordered list ordinals
    ind = " " * indent if indent > 0 else ""  # no negatives allowed

    if ol:
        ord = str(i)
    else:
        ord = bullet
        os = ""

    for r in relations:
        try:
            a = entity_id_map.get(r.from_id, None)
            b = entity_id_map.get(r.to_id, None)
        except Exception as e:
            raise ToolError(f"Failed to get relation entities: {e}")
        if not a or not isinstance(a, Entity):
            logger.error(f"Failed to get 'from' entity ({r.from_id}) from relation")
        if not b or not isinstance(b, Entity):
            logger.error(f"Failed to get 'to' entity ({r.to_id}) from relation")

        # If this is the user-linked entity, use the preferred name instead; if name is missing, use "unknown"
        if a:
            if a.name.lower().strip() == "__user__" or a.name.lower().strip() == "user":
                a_name = user_info.preferred_name + " (user)"
            else:
                a_name = a.name
            a_icon = a.icon_()
            a_id = a.id
            a_type = a.entity_type
        else:
            a_name = "unknown"
            a_icon = ""
            a_id = str(r.from_id)
            a_type = "unknown"
        if b:
            if b.name.lower().strip() == "__user__" or b.name.lower().strip() == "user":
                b_name = user_info.preferred_name
            else:
                b_name = b.name
            b_icon = b.icon_()
            b_id = b.id
            b_type = b.entity_type

        else:
            b_name = "unknown"
            b_icon = ""
            b_id = str(r.to_id)
            b_type = "unknown"

        # Compose pre-entity string (list stuff like indentation, bullet, ordinal, etc.)
        # Special case: if both ul and ol are False, omit pre-relation string
        if not ul and not ol:
            display_pre = ""
        else:
            display_pre: str = f"{ind}{ord}{os} "

        # Resolve entity properties
        

        # Compose relation to and from strings
        if md_links and include_ids:
            link_from = f"[{a_icon}{a_name}]({a_id})"
            link_to = f"[{b_icon}{b_name}]({b_id})"
        elif md_links and not include_ids:
            link_from = f"{a_icon}{a_name}"
            link_to = f"{b_icon}{b_name}"
        else:
            link_from = f"{a_icon}{a_name}"
            link_to = f"{b_icon}{b_name}"
            if include_ids:
                link_from += f" ({a_id})"
                link_to += f" ({b_id})"
        if include_types:
            link_from += f" ({a_type})"
            link_to += f" ({b_type})"

        # Compose entity string (entity icon, name, id, type)
        display = f"{link_from} {r.relation} {link_to}"

        # Compose post-entity string (separator)
        display_post = f"{separator}"

        result += f"{display_pre}{display}{display_post}"
        i += 1

    # Finally, add the epilogue
    result += epilogue

    return result


async def print_relations_between_entities(
    entities: list[Entity],
    relations: list[Relation],
    options: PrintOptions = PrintOptions()
) -> str:
    """
    Print all the relations between a list of two or more entities in a readable format.

    Args:

    - entities: The list of entities to print. Required if relations is not provided.
    - relations: The list of relations to print. Required if entities is not provided.
    - options: The options to use for printing the relations. If not provided, default values will be used.
    """


def __this_is_a_fake_function_to_separate_sections_in_the_outline_in_cursor_do_not_use_me() -> None:
    pass


@mcp.tool
async def read_graph(
    exclude_user_info: bool = Field(
        default=False,
        description="Whether to exclude the user info from the summary. Default is False.",
    ),
    exclude_entities: bool = Field(
        default=False,
        description="Whether to exclude the entities from the summary. Default is False.",
    ),
    exclude_relations: bool = Field(
        default=False,
        description="Whether to exclude the relations from the summary. Default is False.",
    ),
    exclude_observations: bool = Field(
        default=False,
        description="Whether to exclude observations from the summary. Default is False.",
    ),
):
    """Read and print a user/LLM-friendly summary of the entire knowledge graph.

    Args:

        - exclude_user_info: Whether to exclude the user info from the summary. Default is False.
        - exclude_entities: Whether to exclude the entities from the summary. Default is False.
        - exclude_relations: Whether to exclude the relations from the summary. Default is False.
        - exclude_observations: Whether to exclude observations from the summary. Default is False.

    Returns:
        User/LLM-friendly summary of the entire knowledge graph in text/markdown format
    """
    try:
        graph = await manager.read_graph()

        result = ""

        try:
            if not exclude_user_info:
                result += await print_user_info(
                    graph, not exclude_observations, not exclude_relations
                )
        except Exception as e:
            raise ToolError(f"Error while printing user info: {e}")

        # Print all entities
        try:
            if not exclude_entities:
                result += f"\n👤 You've made observations about {len(graph.entities)} entities:\n"
                result += await print_entities(graph.entities)
        except Exception as e:
            raise ToolError(f"Error while printing entities: {e}")

        # Print all relations
        try:
            if not exclude_relations:
                rel_result = await print_relations(graph)
                if rel_result:
                    result += f"\n🔗 You've learned about {len(graph.relations)} relations between these entities:\n"
                    result += rel_result
        except Exception as e:
            raise ToolError(f"Error while printing relations: {e}")
        return result

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
        result_str = await print_user_info(include_observations, include_relations)
    except Exception as e:
        raise ToolError(f"Failed to read user info: {e}")
    return result_str


@mcp.tool
async def create_entities(new_entities: list[CreateEntityRequest]):
    """
    Add new entities (nodes) to the knowledge graph.

    ## Adding Entities

    For each entity to be added:

      - name: entity_name (required)
      - entity_type: entity_type (required)
      - observations (list[Observation]): list of observations about the entity (optional, but recommended)

        Observations require:
        - content: str (required)
        - durability: Literal['temporary', 'short-term', 'long-term', 'permanent'] (optional, defaults to 'short-term')

        * The timestamp will be added automatically

      - aliases: list of str (optional)
      - icon: Emoji to represent the entity (optional)

    Example entity creation request:
    ```json
    [
        {
            "name": "John Doe",
            "entity_type": "person",
            "observations": [
                {
                    "content": "John Doe is a software engineer",
                    "durability": "permanent",
                }
            ],
            "aliases": ["John Smith", "John S."],
            "icon": "🥴",
        }
    ]
    ```
    """
    try:
        entities_created = await manager.create_entities(new_entities)

        succeeded: list[CreateEntityResult] = []
        failed: list[CreateEntityResult] = []
        for r in entities_created:
            if r.errors:
                failed.append(r)
            else:
                succeeded.append(r)

        if len(succeeded) == 0:
            if len(failed) == 0:
                result = "The request was received; however, no new entities were created!\n"
            result = "Request received; however, no new entities were created, due to the following errors:\n"
        elif len(succeeded) == 1:
            result = "Entity created successfully:\n"
        elif len(succeeded) > 1:
            result = f"Created {len(succeeded)} entities successfully:\n"
        for r in succeeded:
            e = Entity.from_dict(r.entity or {})
            icon = e.icon_()
            result += f"{icon}{e.name} ({e.entity_type})\n"
            if e.aliases:
                result += "  Alias(es): "
                result += f"{', '.join([str(a) for a in e.aliases])}\n"
            if e.observations:
                result += "  Observation(s): "
                for o in e.observations:
                    result += f"  - {o.content} ({o.durability.value})\n"
            result += "\n"

        if len(failed) == 0:
            return result
        elif len(failed) == 1:
            result += "Failed to create entity:\n"
        else:
            result += f"Failed to create {len(failed)} entities:\n"
        for r in failed:
            ent = r.entity or {}
            result += f"  - {ent.get('name', 'unknown')} ({ent.get('entity_type', 'unknown')})\n"
            if r.errors:
                result += "Error(s):\n"
                for err in r.errors:
                    result += f"  - {err}\n"
            result += "\n"

        return result
    except Exception as exc:
        raise ToolError(f"Failed to create entities: {exc}")


@mcp.tool
async def create_relations(new_relations: list[CreateRelationRequest]):
    """
    Record relations (edges) between entities in the knowledge graph.

    Args:

      - new_relations: list of CreateRelationRequest objects

        Each relation must be a CreateRelationRequest object with the following properties:

        - from (str): Origin entity name or ID
        - to (str): Destination entity name or ID
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
    except Exception as e:
        raise ToolError(f"Failed to create relations: {e}")

    try:
        if not relations or len(relations) == 0:
            return "Request successful; however, no new relations were added!"
        elif len(relations) == 1:
            result = "Relation created successfully:\n"
        else:
            result = f"Created {len(relations)} relations successfully:\n"

        for r in relations:
            from_e, to_e = await manager.get_entities_from_relation(r)
            result += f"{from_e.icon_()}{from_e.name} ({from_e.entity_type}) {r.relation} {to_e.icon_()}{to_e.name} ({to_e.entity_type})\n"

        return result
    except Exception as e:
        raise ToolError(f"Failed to print relations: {e}")


@mcp.tool
async def add_observations(new_observations: list[ObservationRequest]):
    """
    Add observations about entities or the user (via the user-linked entity) to the knowledge graph.

    Args:

    - new_observations: list of ObservationRequest objects. Each item may specify either
    `entity_id` or `entity_name`. Special-case: `entity_name` may be "user" to target the
    user-linked entity.

    Each observation must be a ObservationRequest object with the following properties:

    - entity_id (str, preferred) or entity_name (str): Target entity; if entity_name is 'user',
      the user-linked entity is used
    - content (str): Observation content (required)
    - durability (Literal['temporary', 'short-term', 'long-term', 'permanent']): Durability of the observation (optional, defaults to 'short-term')

    Either entity_name or entity_id must be provided. 'entity_name' is deprecated and will be removed in a future version.

    Observation `content` must be lowercase, in active voice, exclude the 'from' entity, and concise. Examples:

    - "likes chicken"
    - "enjoys long walks on the beach"
    - "can ride a bike with no handlebars"
    - "wants to be a movie star"
    - "dropped out of college to pursue a career in underwater basket weaving"

    `durability` determines how long the observation is kept in the knowledge graph and should reflect
    the expected amount of time the observation is relevant.

    - 'temporary': The observation is only relevant for a short period of time (1 month)
    - 'short-term': The observation is relevant for a few months (3 months).
    - 'long-term': The observation is relevant for a few months to a year. (1 year)
    - 'permanent': The observation is relevant for a very long time, or indefinitely. (never expires)

    Observations added to non-existent entities will result in the creation of the entity.
    """
    try:
        results = await manager.apply_observations(new_observations)
    except Exception as e:
        raise ToolError(f"Failed to add observations: {e}")

    if not results or len(results) == 0:
        return "Request successful; however, no new observations were added!"
    elif len(results) == 1:
        result = f"Observations added to 1 entity:\n"
    else:
        result = f"Observations added to {len(results)} entities:\n"

    for r in results:
        e = r.entity
        result += print_entities(entities=[e])
        for o in r.added_observations:
            result += f"- {o.content} ({o.durability.value})\n"
        result += "\n"

    return result


# @mcp.tool  # TODO: remove from interface and bury/automate in manager
# async def cleanup_outdated_observations():
#     """Remove observations that are likely outdated based on their durability and age.

#     Returns:
#         Summary of cleanup operation
#     """
#     try:
#         cleanup_result = await manager.cleanup_outdated_observations()
#         ent = cleanup_result.entities_processed_count
#         obs = cleanup_result.observations_removed_count
#         obs_detail = cleanup_result.removed_observations
#         result = (
#             "" if settings.no_emojis else "🧹 "
#         ) + f"Cleaned up {obs} observations from {ent} entities"
#         logger.info(result)
#         logger.debug(f"Removed observations: {obs_detail}")
#         return result
#     except Exception as e:
#         raise ToolError(f"Failed to cleanup observations: {e}")


@mcp.tool
async def get_observations_by_durability(  # TODO: add other sort options, maybe absorb into other tools
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
async def delete_entry(request: DeleteEntryRequest):  # TODO: deprecate! ...or not?
    """Unified deletion tool for observations, entities, and relations. Data must be a list of the appropriate object for each entry_type:

    - 'entity': list of entity IDs
    - 'observation': [{entity_id, [observation content]}]
    - 'relation': [{from_entity(name or alias), to_entity(name or alias), relation}]

    ***CRITICAL: THIS ACTION IS DESTRUCTIVE AND IRREVERSIBLE - ENSURE THAT THE USER CONSENTS PRIOR TO EXECUTION!!!***
    """
    entry_type = request.entry_type
    data = request.data

    try:
        if entry_type == "entity":
            try:
                await manager.delete_entities(data or [])
            except Exception as e:
                raise ToolError(f"Failed to delete entities: {e}")
            return "Entities deleted successfully"

        elif entry_type == "observation":
            await manager.delete_observations(data or [])
            return "Observations deleted successfully"

        elif entry_type == "relation":
            await manager.delete_relations(data or [])
            return "Relations deleted successfully"

        else:
            return ""
    except Exception as e:
        raise ToolError(f"Failed to delete entry: {e}")


@mcp.tool
async def update_user_info(  # NOTE: feels weird, re-evaluate
    preferred_name: str | None = Field(description="Provide a new preferred name for the user."),
    first_name: str | None = Field(
        default=None, description="Provide a new given name for the user."
    ),
    last_name: str | None = Field(
        default=None, description="Provide a new family name for the user."
    ),
    middle_names: list[str] | None = Field(
        default=None, description="Provide new middle names for the user"
    ),
    pronouns: str | None = Field(default=None, description="Provide new pronouns for the user"),
    nickname: str | None = Field(default=None, description="Provide a new nickname for the user"),
    prefixes: list[str] | None = Field(
        default=None, description="Provide new prefixes for the user"
    ),
    suffixes: list[str] | None = Field(
        default=None, description="Provide new suffixes for the user"
    ),
    emails: list[str] | None = Field(
        default=None, description="Provide new email address(es) for the user"
    ),
    linked_entity_id: str | None = Field(
        default=None,
        description="Provide the ID of the new user-linked entity to represent the user.",
    ),
):
    """
    Update the user's identifying information in the graph. This tool should be rarely called, and
    only if it appears that the user's identifying information is missing or incorrect, or if the
    user specifically requests to do so.

    Important:Provided args will overwrite existing user info fields, not append/extend them.

    Args:
      - preferred_name: Provide a new preferred name for the user.

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
      - linked_entity_id: Provide to change the user-linked entity. This should almost NEVER be used, and only if the user specifically requests to do so AND it appears there is a problem with the link. It is always preferable to edit the user-linked entity instead.

      * One of the following MUST be provided: preferred_name, first_name, last_name, or nickname
      * The `names` field will be computed automatically from the provided information. Ignored if provided upfront.

    Returns:
        On success, the updated user info.
        On failure, an error message.

    ## Capturing user info

    When the user provides information about themselves, you should capture information for the
    required fields from their response.

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
    if not preferred_name and not first_name and not nickname and not last_name:
        raise ValidationError(
            "Either a preferred name, first name, last name, or nickname are required"
        )

    new_user_info_dict = {
        "preferred_name": preferred_name,
        "first_name": first_name,
        "last_name": last_name,
        "middle_names": middle_names,
        "pronouns": pronouns,
        "nickname": nickname,
        "prefixes": prefixes,
        "suffixes": suffixes,
        "emails": emails,
        "linked_entity_id": linked_entity_id,
    }

    try:
        new_user_info = UserIdentifier.from_values(**new_user_info_dict)
        result = await manager.update_user_info(new_user_info)
        return str(result)
    except Exception as e:
        raise ToolError(f"Failed to update user info: {e}")


@mcp.tool
async def search_nodes(  # TODO: improve search
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
    entity_names: list[str] | str | None = Field(
        default=None,
        description="List of entity names or aliases to retrieve",
    ),
    entity_ids: list[str | EntityID] | str | EntityID | None = Field(
        default=None,
        description="List of entity IDs to retrieve",
    ),
):
    """
    Open specific nodes (entities) in the knowledge graph by their IDs, names, or aliases.

    Args:
        entity_names: List of entity names or aliases to retrieve
        entity_ids: List of entity IDs to retrieve

    If both entity_names and entity_ids are provided, both will be used to filter the entities.

    Returns:
        Data (observations) about the nodes (entities) and their relationships (relations) with other nodes in the graph.
    """

    try:
        opened_nodes, node_relations = await manager.open_nodes(entity_names, entity_ids)
    except Exception as e:
        raise ToolError(f"Failed to open nodes: {e}")

    # Print the results
    result_str = ""
    result_str += await print_entities(entities=opened_nodes)
    result_str += await print_relations(relations=node_relations)

    return result_str


@mcp.tool
async def merge_entities(
    new_entity_name: str = Field(
        description="Name of the new merged entity (must not conflict with an existing name or alias unless part of the merge)"
    ),
    entity_ids: list[EntityID | str] | EntityID | str = Field(
        description="IDs of entities to merge into the new entity"
    ),
):
    """Merge a list of entities into a new entity with the provided name.

    The manager will combine observations and update relations to point to the new entity.
    """
    try:
        entities: list[Entity] = await manager.get_entities(entity_ids)
        merged = await manager.merge_entities(new_entity_name, entities)
    except Exception as e:
        raise ToolError(f"Failed to merge entities: {e}")
    return_str = f"Successfully merged {len(entities)} entities into a new entity:\n"
    return_str += print_entities(entities=[merged])
    return return_str


@mcp.tool
async def update_entity(
    identifier: str | None = Field(
        default=None,
        description="Entity name or alias to identify the target entity (used if entity_id not provided)",
    ),
    entity_id: str | None = Field(
        default=None,
        description="ID of the target entity (preferred over identifier if provided)",
    ),
    name: str | None = Field(default=None, description="New canonical name for the entity"),
    entity_type: str | None = Field(default=None, description="New type for the entity"),
    aliases: str | list[str] | None = Field(
        default=None,
        description="Aliases to set (merged by default; set merge_aliases=false to replace)",
    ),
    icon: str | None = Field(
        default=None,
        description="Emoji icon to set for the entity; use empty string to clear",
    ),
    merge_aliases: bool = Field(
        default=True,
        description="When true, merge provided aliases; when false, replace alias list",
    ),
):
    """Update fields on an existing entity by ID or name/alias.

    Provide at least one of: `name`, `entity_type`, `aliases`, or `icon`.
    """
    try:
        if name is None and entity_type is None and aliases is None and icon is None:
            raise ValidationError("No updates provided")

        # Normalize aliases to a list[str] if provided as a string (e.g., stringified JSON array)
        aliases_normalized: list[str] | None
        if isinstance(aliases, str):
            try:
                parsed = json.loads(aliases)
                if isinstance(parsed, list):
                    aliases_normalized = [str(a) for a in parsed]
                else:
                    # Fallback: comma-separated string
                    aliases_normalized = [s.strip() for s in aliases.split(",") if s.strip()]
            except Exception:
                aliases_normalized = [s.strip() for s in aliases.split(",") if s.strip()]
        else:
            aliases_normalized = aliases

        updated = await manager.update_entity(
            identifier=identifier,
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            aliases=aliases_normalized,
            icon=icon,
            merge_aliases=merge_aliases,
        )

        # Build a concise human-readable summary
        result = f"Updated entity: {updated.icon_()}{updated.name} ({updated.entity_type})\n"
        if updated.aliases:
            result += "  Aliases: " + ", ".join(updated.aliases) + "\n"
        return result
    except (KnowledgeGraphException, ValueError) as e:
        raise ToolError(f"Failed to update entity: {e}")
    except Exception as e:
        raise ToolError(f"Unexpected error during entity update: {e}")


# ----- DEBUG/EXPERIMENTAL TOOLS -----#

if settings.debug:

    @mcp.tool
    async def DEBUG_get_email_update():
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

    # @mcp.tool
    # async def DEPRECATED_create_entry(request: CreateEntryRequest):
    #     """Add entities, observations, or relations to the knowledge graph.

    #     'data' must be a list of the appropriate object for each entry_type:

    #     ## Adding Observations
    #     'data' must be a list of observations:
    #     - entity_name: entity_name (required)
    #     - content: str (required)
    #     - durability: Literal['temporary', 'short-term', 'long-term', 'permanent'] (optional, defaults to 'short-term')

    #     Observation content must be in active voice, excule the 'from' entity, lowercase, and should be concise and to the point. Examples:
    #     - "likes chicken"
    #     - "enjoys long walks on the beach"
    #     - "can ride a bike with no handlebars"
    #     - "wants to be a movie star"
    #     - "dropped out of college to pursue a career in underwater basket weaving"

    #     Durability determines how long the observation is kept in the knowledge graph and should reflect
    #     the expected amount of time the observation is relevant.
    #     - 'temporary': The observation is only relevant for a short period of time (1 month)
    #     - 'short-term': The observation is relevant for a few months (3 months).
    #     - 'long-term': The observation is relevant for a few months to a year. (1 year)
    #     - 'permanent': The observation is relevant for a very long time, or indefinitely. (never expires)

    #     """
    #     logger.warning(
    #         "This tool is deprecated and will be removed in a future version. Use the create_entities, create_relations, and apply_observations tools instead."
    #     )

    #     entry_type = request.entry_type
    #     data = request.data
    #     try:
    #         if entry_type == "observation":
    #             observation_result: list[AddObservationResult] = await manager.apply_observations(
    #                 data
    #             )
    #             result = ""
    #             for r in observation_result:
    #                 result += str(r) + "\n"

    #         elif entry_type == "entity":
    #             entity_result: CreateEntityResult = await manager.create_entities(data)
    #             result = str(entity_result)

    #         elif entry_type == "relation":
    #             relation_result: CreateRelationResult = await manager.create_relations(data)
    #             result = str(relation_result)

    #         else:
    #             raise ValueError(f"Invalid entry type: {entry_type}")

    #     except Exception as e:
    #         raise ToolError(f"Failed to create entry: {e}")

    #     return result

    @mcp.tool
    async def DEBUG_save_graph():
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
