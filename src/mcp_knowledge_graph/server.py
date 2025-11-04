"""
FastMCP Server implementation for temporal knowledge graph memory.

This module implements the Model Context Protocol server that exposes
knowledge graph operations as tools for LLM integration using FastMCP 2.11.
"""

import sys
import asyncio
import json
import re
from datetime import tzinfo, datetime, timezone, timedelta
from fastmcp import FastMCP
from pydantic import Field
from pydantic.main import IncEx
from pydantic.dataclasses import dataclass
from typing import Any
from fastmcp.exceptions import ToolError, ValidationError

from .logging import logger
from .manager import KnowledgeGraphManager
from .models import (
    DeleteEntryRequest,
    DeleteObservationRequest,
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
    Observation,
    UpdateEntityRequest,
)
from .settings import Settings as settings
from .settings import IQ_MCP_VERSION


from .supabase import SupabaseManager, EmailSummary

supabase_manager: SupabaseManager | None = (
    SupabaseManager(settings.supabase) if settings.supabase else None
)


# Load settings once and configure logging level accordingly


# Initialize the knowledge graph manager and FastMCP server
manager = KnowledgeGraphManager(settings.memory_path)

# Create FastMCP server instance
mcp = FastMCP(name="iq-mcp", version=IQ_MCP_VERSION)


@dataclass
class PrintOptions:
    """
    Options for printing things such as entities, relations, or observations from the knowledge graph.
    All options are optional, and the default values are used if not specified.

    Parameters:

    - exclude_user: Whether to exclude the user from the entity list. Default is `True`.
    - prologue: A string added before the entity list. Default is `None`.
    - separator: The separator to use between list items (entities). Default is `\\n`.
    - epilogue: A string added after the entity list. Default is `\\n\\n`.
    - md_links: Whether to use markdown-style links for the entities. Default is `True`.
    - include_ids: Whether to include the IDs of the entities in the display. Default is `True`.
    - include_types: Whether to include the types of the entities in the display. Default is `True`.
    - include_observations: Whether to include observations of the entities in the display. Default is `False`.
    - include_relations: Whether to include relations of the entities in the display. Default is `False`.
    - include_durability: Whether to include the durability of the observations in the display, if applicable. Default is `True`.
    - include_ts: Whether to include the timestamp of the observations in the display, if applicable. Default is `True`.
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

    exclude_user: bool = False
    prologue: str = ""
    separator: str = "\n"
    epilogue: str = "\n\n"
    md_links: bool = True
    include_ids: bool = True
    include_types: bool = True
    include_observations: bool = False
    include_relations: bool = False
    include_durability: bool = True
    include_ts: bool = True
    indent: int = 0
    ul: bool = True
    ol: bool = False
    bullet: str = "-"
    ordinal_separator: str = "."


#### Helper functions ####
async def print_entities(
    entities: list[Entity] | None = None,
    graph: KnowledgeGraph | None = None,
    options: PrintOptions = PrintOptions(),
    exclude_user: bool | None = None,
):
    """
    Print entity data from a list of entities in a readable format. If no entities are provided, all entities from the graph will be printed.

    Various options are available to customize the display. All options are optional, and the
    default values are used if not specified.

    Args:

    - graph: The knowledge graph to print entities from. Required if entities is not provided.
    - entities: The list of entities to print. Required if graph is not provided.
    - options: The options (PrintOptions object)to use for printing the entities. If not provided, default values will be used.
    - exclude_user: Whether to skip printing the user-linked entity data. If not provided, default PrintOptions value will be used. Provided here for convenience, but can be set in the options object.

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

    if not entities:
        graph = graph or await manager.read_graph()
        entities = graph.entities
        logger.debug(f"Printing all entities from graph {str(graph)}")
    else:
        e_names = []
        for e in entities:
            e_names.append(e.name)
        logger.debug(f"Printing provided entities: {', '.join(e_names)}")

    if not entities:
        raise ToolError("No entities provided")
    else:
        e_names = []
        for e in entities:
            e_names.append(e.name)
        logger.debug(f"Printing entities: {', '.join(e_names)}")

    if exclude_user is None:
        exclude_user = options.exclude_user

    # Resolve options
    prologue = options.prologue
    separator = options.separator
    epilogue = options.epilogue
    md_links = options.md_links
    include_ids = options.include_ids
    include_types = options.include_types
    include_observations = options.include_observations
    include_durability = options.include_durability
    include_ts = options.include_ts
    # include_relations = options.include_relations
    ind = " " * options.indent if options.indent > 0 else ""
    ul = options.ul
    ol = options.ol if ul else ""
    bullet = options.bullet
    os = options.ordinal_separator if ol else ""

    # Start rendering
    result = prologue
    try:
        i = 1
        for e in entities:
            ord = i if ol else bullet
            if e.name.lower().strip() == "__user__" or e.name.lower().strip() == "user":
                if exclude_user is True:
                    logger.debug(
                        "print_entities: User-linked entity found during entity printing, skipping"
                    )
                    continue
                else:
                    logger.debug(
                        "print_entities: User-linked entity found during entity printing, including"
                    )
                    graph = graph or await manager.read_graph()
                    user_info = graph.user_info
                    id = user_info.linked_entity_id
                    icon = e.icon_()
                    name = user_info.preferred_name
                    type = "user"
            else:
                id = e.id
                icon = e.icon_()
                name = e.name
                type = e.entity_type

            # Compose pre-entity string (indentation, bullet, ordinal, spacer)
            # Special case: if both ul and ol are False, omit pre-entity string
            if not ul and not ol:
                display_pre = ""
            else:
                display_pre: str = f"{ind}{ord}{os} "

            # Compose entity string (entity icon, name, id, type)
            display = (
                f"{'[' if md_links else ''}"
                f"{icon}{name}"
                f"{' (' + type + ')' if include_types else ''}"
                f"{']' if md_links else ' '}"
                f"{'(id:' + id + ')' if include_ids else ''}"
            )
            # With default options: [👤 John Doe](12345678) (person)
            # Example with md_links=False: 👤 John Doe (person, ID: 12345678)

            # Compose post-entity string (separator)
            display_post = f"{separator}"

            result += f"{display_pre}{display}{display_post}"

            # Print the entity's observations
            if include_observations:
                result += await print_observations(
                    e.observations,
                    options=PrintOptions(
                        include_durability=include_durability,
                        include_ts=include_ts,
                    ),
                )

            # Print relations about the entity (dynamic, from graph relations)
            # TODO: implement - probably want to robustly remove duplicates
            # if include_relations: ...
            i += 1

        # Finally, add the epilogue
        result += epilogue

        return result
    except Exception as e:
        raise ToolError(f"Failed to print entities: {e}")


async def print_relations(
    relations: list[Relation] | None = None,
    graph: KnowledgeGraph | None = None,
    options: PrintOptions = PrintOptions(),
) -> str:
    """
    Print relations from the graph, or from a list of relations, in a readable format. Resolves entity IDs to names wherever possible.
    If no arguments are provided, the graph will be read and all relations will be printed.

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
    graph = graph or await manager.read_graph()
    relations = relations or graph.relations
    user_info = graph.user_info
    entity_id_map = await manager.get_entity_id_map(graph)

    # Resolve formatting options
    prologue = options.prologue
    epilogue = options.epilogue
    md_links = options.md_links
    include_ids = options.include_ids
    include_types = options.include_types
    indent = options.indent
    ul = options.ul
    ol = options.ol if ul else ""
    bullet = options.bullet
    os = options.ordinal_separator
    separator = options.separator
    i = 1  # for ordered list ordinals
    ind = " " * indent if indent > 0 else ""  # no negatives allowed
    if ol:
        ord = str(i)
    else:
        ord = bullet
        os = ""

    lines: list[str] = [prologue]
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

        # For A: If this is the user-linked entity, use the user's preferred name instead; if name is missing, use "unknown"
        if a.name.lower().strip() == "__user__" or a.name.lower().strip() == "user":
            a_name = user_info.preferred_name + " (user)"
        else:
            a_name = a.name

        # For B: If this is the user-linked entity, use the user's preferred name instead; if name is missing, use "unknown"
        if b.name.lower().strip() == "__user__" or b.name.lower().strip() == "user":
            b_name = user_info.preferred_name + " (user)"
        else:
            b_name = b.name

        a_icon = a.icon_()
        a_id = a.id
        a_type = a.entity_type

        b_icon = b.icon_()
        b_id = b.id
        b_type = b.entity_type

        # Compose pre-entity string (list stuff like indentation, bullet, ordinal, etc.)
        # Special case: if both ul and ol are False, omit pre-relation string
        if not ul and not ol:
            display_pre = ""
        else:
            display_pre: str = f"{ind}{ord}{os} "

        # Resolve entity properties

        # Compose relation to and from strings
        if md_links and include_ids:
            link_from = f"[{a_icon}{a_name}](id:{a_id})"
            link_to = f"[{b_icon}{b_name}](id:{b_id})"
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
        lines.append(f"{display_pre}{link_from} {r.relation} {link_to}")
        i += 1

    # Finally, add the epilogue
    result = separator.join(lines) + epilogue

    return result


async def print_observations(
    observations: list[Observation], options: PrintOptions = PrintOptions()
) -> str:
    """
    Print all the observations of an entity in a readable format.

    Args:

    - observations: The list of observations to print. Required.
    - options: The options to use for printing the observations. If not provided, default values will be used.
    """

    # Resolve options
    prologue = options.prologue
    epilogue = options.epilogue
    ul = options.ul
    ol = False if ul else options.ol
    bullet = options.bullet
    separator = options.separator

    os = options.ordinal_separator if ol else ""
    ind = " " * options.indent if options.indent > 0 else ""

    result_str = prologue
    i = 1
    for o in observations:
        try:
            ord = str(i) if ol else bullet
            pre = f"{ind}{ord}{os} "
            content = o.content

            # Optional display of durability and timestamp (enabled by default)
            if options.include_durability or options.include_ts:
                content_items = []
                if options.include_ts:
                    content_items.append(o.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                if options.include_durability:
                    content_items.append(o.durability.value)
                content += f" ({', '.join(content_items)})"
            post = f"{separator}"
            result_str += f"{pre}{content}{post}"
            i += 1
        except Exception as e:
            logger.error(
                f"Error printing observation {i} from list of {len(observations)} observations: {e}"
            )
    result_str += epilogue
    return result_str


async def print_email_summaries(
    email_summaries: list[EmailSummary], options: PrintOptions = PrintOptions()
) -> str:
    """Print email summaries in a readable format."""
    # Resolve formatting options

    sep = options.separator
    if options.indent and options.indent > 0:
        ind = " " * options.indent
    else:
        ind = ""
    ol = options.ol
    if ol:
        os = options.ordinal_separator + " "
    else:
        os = " "

    lines: list[str] = []
    i = 1
    for summary in email_summaries:
        ord = str(i) if ol else options.bullet
        ind2_len = len(ind + ord + os)
        ind2 = " " * ind2_len if ind2_len > 0 else ""
        ts = datetime.fromisoformat(summary.timestamp) if summary.timestamp else None
        if ts:
            ts = ts.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
        else:
            ts = "N/A"
        if not summary.summary:
            logger.error(
                f"EmailSummary for message ID {summary.message_id} has no content summary!"
            )
            continue
        lines.append(f"{ind}{ord}{os}Message ID: {summary.message_id}")
        lines.append(
            f"{ind2}From: {'[' + summary.from_name + ']' if options.md_links else summary.from_name}"
            + f"{f'(mailto:{summary.from_address})' if options.md_links else f' ({summary.from_address})'}"
        )
        lines.append(f"{ind2}Reply-To: {summary.reply_to or 'N/A'}")
        lines.append(f"{ind2}Received at: {ts}")
        lines.append(f"{ind2}Subject: {summary.subject or ''}")
        lines.append(f"{ind2}Content summary: {summary.summary}")

        parsed_links: list[str] = []
        for link in summary.links or []:
            title = link.get("title") or ""
            url = link.get("url") or str(link) or ""
            if not url:
                continue
            elif title and url and options.md_links:
                parsed_links.append(f"{ind2}- [{title}]({url})")
            elif title and url and not options.md_links:
                parsed_links.append(f"{ind2}- {title}: {url}")
            elif not title and url:
                parsed_links.append(f"{ind2}- {url}")
            else:
                continue
        lines.append(f"{ind2}Links:")
        lines.append(f"{sep.join(parsed_links)}")
        i += 1
    return sep.join(lines)


async def print_user_info(
    graph: KnowledgeGraph | None = None,
    include_observations: bool = True,
    options: PrintOptions = PrintOptions(),
):
    """Get the user's info from the provided knowledge graph (or the default graph from the manager) and print to a string.

    Args:
      - graph: The knowledge graph to print user info from. Will load default graph from manager if not provided.
      - include_observations: Include observations related to the user in the response.
      - include_relations: Include relations related to the user in the response.
      - options: The options to use for printing the user info. If not provided, default values will be used.
    """

    if not graph:
        graph = await manager.read_graph()
    entity_id_map = await manager.get_entity_id_map(graph)

    # Resolve options
    prologue = options.prologue
    epilogue = options.epilogue
    separator = options.separator
    indent = options.indent
    ul = options.ul
    ol = False if ul else options.ol
    bullet = options.bullet
    ordinal_separator = options.ordinal_separator

    ind = " " * indent if indent > 0 else ""
    os = ordinal_separator if ol else ""
    ord = "" if ol else bullet

    try:
        # Compose a sensible display name for the user, based on available data and preferences
        last_name = graph.user_info.last_name or ""
        first_name = graph.user_info.first_name or ""
        nickname = graph.user_info.nickname or ""
        preferred_name = graph.user_info.preferred_name or (
            nickname or first_name or last_name or "user"
        )
        linked_entity_id = graph.user_info.linked_entity_id
        middle_names = graph.user_info.middle_names or []
        pronouns = graph.user_info.pronouns or ""
        emails = graph.user_info.emails or []
        prefixes = graph.user_info.prefixes or []
        suffixes = graph.user_info.suffixes or []
        names = graph.user_info.names or [preferred_name]
    except Exception as e:
        raise ToolError(f"Failed to load user info: {e}")

    try:
        linked_entity = entity_id_map.get(linked_entity_id, None)
        if not linked_entity:
            raise KnowledgeGraphException("User-linked entity not found! Graph may be corrupt!")
    except Exception as e:
        raise ToolError(f"Failed to get user-linked entity: {e}")

    lines: list[str] = []
    if prologue:
        lines.append(prologue)

    # Start with printing the user's info
    try:
        lines.append(f"{names[0]} (Preferred name: {preferred_name})")
        if middle_names:
            lines.append(f"Middle name(s): {', '.join(middle_names)}")
        if nickname and nickname != preferred_name:
            lines.append(f"Nickname: {nickname}")
        if pronouns:
            lines.append(f"Pronouns: {pronouns}")
        if prefixes:
            lines.append(f"Prefixes: {', '.join(prefixes)}")
        if suffixes:
            lines.append(f"Suffixes: {', '.join(suffixes)}")
        if names[1:]:
            lines.append("May also go by:")
            for name in names[1:]:
                lines.append(f"{ind}{ord}{os} {name}")
        if emails:
            lines.append(f"Email addresses: {', '.join(emails)}")
    except Exception as e:
        raise ToolError(f"Failed to print user info: {e}")

    # Print observations about the user (from the user-linked entity)
    try:
        if include_observations and linked_entity:
            if linked_entity.observations:
                lines.append("")
                lines.append("" if settings.no_emojis else "🔍 " + "Observations about the user:")
                for o in linked_entity.observations:
                    ts = o.timestamp.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
                    lines.append(f"{ind}{ord}{os} {o.content} ({ts}, {o.durability.value})")
            else:
                pass  # No observations found in user-linked entity
    except Exception as e:
        raise ToolError(f"Failed to print user observations: {e}")
    lines.append(epilogue)
    return separator.join(lines)


def __this_is_a_fake_function_to_separate_sections_in_the_outline_in_cursor_do_not_use_me() -> None:
    pass


# ------------------------------------


@mcp.tool
async def read_user_info(include_observations: bool = False, include_relations: bool = False):
    """Read the user info from the graph.

    Args:
      - include_observations: Include observations related to the user in the response.
      - include_relations: Include relations related to the user in the response.
    """
    try:
        result_str = await print_user_info(
            include_observations=include_observations, include_relations=include_relations
        )
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
        - durability: Literal['temporary', 'short-term', 'long-term', 'permanent'] (optional but recommended, defaults to 'short-term')

        * The timestamp will be added automatically

      - aliases: list of str (optional)
      - icon: Emoji to represent the entity (optional)

    ## Entity IDs

    Entity IDs are automatically generated by the knowledge graph manager and are unique to each entity. They are not provided in the request.
    Entity IDs provide a way to easily reference specific entities in the knowledge graph.
    """
    if not isinstance(new_entities, list) or not isinstance(new_entities[0], CreateEntityRequest):
        raise ToolError("new_entities must be a list of CreateEntityRequest objects")

    try:
        entities_created = await manager.create_entities(new_entities)
    except Exception as e:
        raise ToolError(f"Failed to create entities: {e}")

    succeeded: list[CreateEntityResult] = []
    failed: list[CreateEntityResult] = []

    for e in entities_created:
        if e.errors:
            failed.append(e)
        else:
            succeeded.append(e)

    # FIX: Variable name collision - use different variable name for result string
    result_str = ""

    if len(succeeded) == 1:
        result_str = "Entity created successfully:\n"
    elif len(succeeded) > 1:
        result_str = f"Created {len(succeeded)} entities successfully:\n"
    if len(succeeded) == 0:
        if len(failed) > 0:
            errmsg = "Request received; however, no new entities were created, due to the following errors:\n"
            for e in failed:
                errmsg += f"- {str(e.entity)}:\n"
                for err in e.errors:
                    errmsg += f"  - {err}\n"
            raise ToolError(errmsg)
        else:
            raise ToolError("Unknown error while creating entities!")

    # On success print the new entities and their observations
    # Extract actual entities from the results
    successful_entities = []
    for result in succeeded:
        if isinstance(result.entity, Entity):
            successful_entities.append(result.entity)
        elif isinstance(result.entity, dict):
            # Convert dict to Entity if needed
            try:
                entity = Entity.from_dict(result.entity)
                successful_entities.append(entity)
            except Exception as e:
                logger.error(f"Failed to convert entity dict to Entity: {e}")

    result_str += await print_entities(
        entities=successful_entities, options=PrintOptions(include_observations=True)
    )

    if len(failed) == 0:
        return result_str
    elif len(failed) == 1:
        result_str += "Failed to create entity:\n"
    else:
        result_str += f"Failed to create {len(failed)} entities:\n"
    for r in failed:
        result_str += f"  - {str(r.entity)}:\n"
        if r.errors:
            result_str += "Error(s):\n"
            for err in r.errors:
                result_str += f"  - {err}\n"
        result_str += "\n"

    return result_str


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

    failed = [r for r in results if r.errors]
    for r in failed:
        logger.error(f"Error adding observations to entity: {'; '.join(r.errors)}")
    succeeded = [r for r in results if not r.errors]

    def dump_bad_entity(entity: Any) -> str:
        if isinstance(entity, dict):
            try:
                _ = Entity.from_dict(entity)
            except Exception:
                pass
            else:
                logger.warning(
                    f"Dumping entity {str(entity)[:20]}... as bad entity; however, it may be valid"
                )
                return json.dumps(
                    entity.model_dump(
                        indent=0,
                        include=IncEx("name", "id", "entity_type"),
                        exclude_none=True,
                        exclude_defaults=True,
                        exclude_unset=True,
                        warnings=False,
                    ),
                    indent=0,
                    separators=(",", ":"),
                )

        elif isinstance(entity, Entity):
            logger.error(
                f"Dumping entity {str(entity)[:20]}... as bad entity; however, it is valid"
            )
            return json.dumps(
                entity.model_dump(
                    exclude_none=True, exclude_defaults=True, exclude_unset=True, warnings=False
                ),
                indent=0,
                separators=(",", ":"),
            )
        else:
            return str(entity)

    # Print the results of adding observations to entities
    result_str = ""
    if len(failed) == 0 or not failed:
        if len(succeeded) == 1:
            ident = f"{succeeded[0].entity.name} (ID: {succeeded[0].entity.id})"
            result_str = f"Succcessfully added observations to {ident}:\n"
            result_str += await print_observations(succeeded[0].added_observations)
        elif len(succeeded) > 1:
            idents = [f"{s.entity.name} ({s.entity.id})" for s in succeeded]
            result_str = f"Succcessfully added observations to {', '.join(idents)}:\n"
            for s in succeeded:
                result_str += f"- {s.entity.name} (ID: {s.entity.id}):\n"
                result_str += await print_observations(s.added_observations)
        else:
            raise ToolError(
                "Unknown issue while printing observation addition results, however no errors were returned!"
            )
    elif len(failed) > 0:
        if len(succeeded) == 0 and len(failed) > 0:
            result_str = "Request successful; however, no new observations were added, due to the following errors:\n"
            for f in failed:
                result_str += f"- {dump_bad_entity(f.entity)}: {'; '.join(f.errors)}\n"
            return result_str
        elif len(succeeded) > 0:
            idents_succeeded = [f"{s.entity.name} (ID: {s.entity.id})" for s in succeeded]
            result_str = f"Successfully added observations to {', '.join(idents_succeeded)}:\n"
            for s in succeeded:
                result_str += f"- {s.entity.name} (ID: {s.entity.id}):\n"
                result_str += await print_observations(s.added_observations)

            result_str += f"However, failed to add observations to {len(failed)} entities:\n"
            for r in failed:
                result_str += f"- {r.entity.name} (ID: {r.entity.id}): {'; '.join(r.errors)}\n"
            return result_str

    return result_str


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


# @mcp.tool
# async def get_observations_by_durability(  # TODO: add other sort options, maybe absorb into other tools
#     entity_name: str = Field(description="The name or alias of the entity to get observations for"),
# ) -> str:
#     """Get observations for an entity grouped by their durability type.

#     Args:
#         entity_name: The name or alias of the entity to get observations for

#     Returns:
#         Observations grouped by durability type
#     """
#     try:
#         result = await manager.get_observations_by_durability(entity_name)
#         return str(result)
#     except Exception as e:
#         raise ToolError(f"Failed to get observations: {e}")


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
            # Ensure data is properly typed as DeleteObservationRequest objects
            if data is None:
                data = []
            # Validate that data contains DeleteObservationRequest objects
            validated_data = []
            for item in data:
                if isinstance(item, DeleteObservationRequest):
                    validated_data.append(item)
                else:
                    # Try to convert dict to DeleteObservationRequest
                    try:
                        if isinstance(item, dict):
                            validated_data.append(DeleteObservationRequest(**item))
                        else:
                            logger.error(f"Invalid observation deletion data: {item}")
                    except Exception as e:
                        logger.error(f"Failed to convert observation deletion data: {e}")
            await manager.delete_observations(validated_data)
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
    entity_ids: list[str] | str | None = Field(
        default=None,
        description="List of IDs of entities to retrieve",
    ),
    entity_names: list[str] | str | None = Field(
        default=None,
        description="List of names or aliases of entities to retrieve. Prefer to use IDs when appropriate.",
    ),
    exclude_relations: bool = Field(
        default=False,
        description="Whether to exclude relations from the summary. Relations are included by default.",
    ),
):
    """
    Open specific nodes (entities) in the knowledge graph by their IDs, names, or aliases.

    Args:
        entity_names: List of names or aliases of entities to retrieve. Prefer to use IDs when appropriate.
        entity_ids: List of IDs of entities to retrieve.

    If both entity_names and entity_ids are provided, both will be used to filter the entities.

    Returns:
        Data (observations) about the nodes (entities) and their relationships (relations) with other nodes in the graph.
    """
    # Handle entity_ids parameter
    resolved_ids = []
    if entity_ids:
        if isinstance(entity_ids, list):
            resolved_ids = entity_ids
        else:
            # Single string ID
            resolved_ids = [entity_ids]

    # Handle entity_names parameter
    resolved_names = []
    if entity_names:
        if isinstance(entity_names, list):
            resolved_names = entity_names
        else:
            # Single string name
            resolved_names = [entity_names]

    try:
        ents = await manager.open_nodes(names=resolved_names, ids=resolved_ids)
    except Exception as e:
        raise ToolError(f"Failed to open nodes: {e}")

    if not exclude_relations:
        rels = await manager.get_relations_from_entities(entities=ents)
    else:
        rels = []

    if not ents:
        raise ToolError("No entities found")
    else:
        if len(ents) == 1:
            result_str = "💭 You remember the following information about this entity:\n"
        elif len(ents) > 1:
            result_str = "💭 You remember the following information about these entities:\n"
        else:
            raise ToolError("No entities found")
        result_str += await print_entities(entities=ents, exclude_user=False)
    if not rels:
        if not exclude_relations:
            logger.error(f"No relations found for the opened nodes {str(ents)}")
        else:
            logger.debug(f"Skipped loading relations for {str(ents)} per llm request")
    else:
        result_str += (
            "🔗 You've learned about the following relationships between these entities:\n"
        )
        result_str += await print_relations(relations=rels)

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
        # Convert entity_ids to a list if it's a single value
        if isinstance(entity_ids, (str, EntityID)):
            entity_ids = [entity_ids]

        # Get entities by IDs to get their names
        entities = await manager.open_nodes(ids=entity_ids)
        if not entities:
            raise ToolError("No entities found with the provided IDs")

        # Extract entity names for the merge operation
        entity_names = [entity.name for entity in entities]

        # Merge entities using their names
        merged = await manager.merge_entities(new_entity_name, entity_names)
    except Exception as e:
        raise ToolError(f"Failed to merge entities: {e}")

    return_str = f"Successfully merged {len(entities)} entities into a new entity:\n"
    return_str += await print_entities(entities=[merged])
    return return_str


@mcp.tool
async def update_entity(request: UpdateEntityRequest):
    """Update fields on an existing entity by ID or name/alias.

    Provide at least one of: `name`, `entity_type`, `aliases`, or `icon`.
    """
    try:
        if all(
            request.new_name is None
            and request.new_type is None
            and request.new_aliases is None
            and request.new_icon is None
        ):
            raise ValidationError("No updates provided")

        # Normalize aliases to a list[str] if provided as a string (e.g., stringified JSON array)
        aliases_normalized: list[str] | None
        if isinstance(request.new_aliases, str):
            try:
                parsed = json.loads(request.new_aliases)
                if isinstance(parsed, list):
                    aliases_normalized = [str(a) for a in parsed]
                else:
                    # Fallback: comma-separated string
                    aliases_normalized = [
                        s.strip() for s in request.new_aliases.split(",") if s.strip()
                    ]
            except Exception:
                aliases_normalized = [
                    s.strip() for s in request.new_aliases.split(",") if s.strip()
                ]
        else:
            aliases_normalized = request.new_aliases

        updated = await manager.update_entity(
            identifier=request.identifier,
            entity_id=request.entity_id,
            name=request.new_name,
            entity_type=request.new_type,
            aliases=aliases_normalized,
            icon=request.new_icon,
            merge_aliases=request.merge_aliases,
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


# ----- EXPERIMENTAL/DEV/WIP TOOLS -----#


# Supabase Integration Tools
from .supabase import SupabaseManager


def add_supabase_tools(mcp_server: FastMCP, supabase_manager: SupabaseManager | None) -> None:
    """If the Supabase integration is enabled, adds the tools to the given MCP server."""

    if not supabase_manager:
        logger.warning(
            "Supabase integration is not initialized, Supabase tools will not be available"
        )
        return

    # Tools to be added with successful Supabase integration
    @mcp_server.tool
    async def get_new_email_summaries(
        from_date: str | None = Field(
            default=None,
            description=(
                "Start date for fetching summaries. Accepts 'YYYY-MM-DD', ISO 8601, or relative phrases like 'one week ago'."
            ),
        ),
        to_date: str | None = Field(
            default=None,
            description=(
                "End date for fetching summaries. Accepts 'YYYY-MM-DD', ISO 8601, or relative phrases like 'yesterday'."
            ),
        ),
        include_reviewed: bool = Field(
            default=False,
            description="Whether to include previously reviewed email summaries. Default is False.",
        ),
    ):
        """Retrieve email summaries from Supabase via the Supabase manager and present them as text."""

        def _parse_date(dt_str: str | None) -> datetime | None:
            if not dt_str:
                return None
            s = dt_str.strip()
            if not s:
                return None

            # Try ISO 8601 with optional trailing Z
            s_iso = s
            if s_iso.endswith("Z"):
                s_iso = s_iso[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(s_iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass

            # Try YYYY-MM-DD date-only
            try:
                dt = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass

            # Simple relative phrases  TODO: improve
            now_utc = datetime.now(timezone.utc)
            s_lower = s.lower()

            if s_lower == "today":
                return now_utc
            if s_lower == "yesterday":
                return now_utc - timedelta(days=1)

            m = re.match(r"^(?P<num>\d+)\s+day(s)?\s+ago$", s_lower)
            if m:
                return now_utc - timedelta(days=int(m.group("num")))

            m = re.match(r"^(?P<num>\d+)\s+week(s)?\s+ago$", s_lower)
            if m:
                return now_utc - timedelta(weeks=int(m.group("num")))

            if s_lower in {"one day ago", "a day ago"}:
                return now_utc - timedelta(days=1)
            if s_lower in {"one week ago", "a week ago", "last week"}:
                return now_utc - timedelta(weeks=1)

            logger.error(f"Unrecognized date format: {dt_str}")
            return None

        start_dt = _parse_date(from_date)
        end_dt = _parse_date(to_date)

        # Retrieve email summaries
        try:
            summaries = await supabase_manager.get_email_summaries(
                from_date=start_dt, to_date=end_dt, include_reviewed=include_reviewed
            )
        except Exception as e:
            raise ToolError(f"Failed to retrieve email summaries: {e}")

        if not summaries:
            return "No new email summaries available!"
        else:
            lines = [f"📧 {len(summaries)} new messages found!"]

        # Format the email summaries
        lines.append(await print_email_summaries(summaries))
        logger.info(
            f"Marking {len(summaries)} email summaries as reviewed in Supabase in background..."
        )
        asyncio.create_task(supabase_manager.mark_as_reviewed(summaries))
        result = "\n".join(lines) + "\n"
        return result

    @mcp_server.tool
    async def sync_supabase():
        """Replace Supabase KG tables with a cleaned snapshot from the local knowledge graph."""
        try:
            graph = await manager.read_graph()
            result = await supabase_manager.sync_knowledge_graph(graph)
            return result
        except Exception as e:
            raise ToolError(f"Failed to sync Supabase: {e}")
        
    @mcp_server.tool
    async def read_supabase_graph():
        """Read the knowledge graph from Supabase and return it as a text string."""
        try:
            result = await supabase_manager.get_knowledge_graph()
            return result
        except Exception as e:
            raise ToolError(f"Failed to read Supabase graph: {e}")


# ----- KEEP AT THE END AFTER OTHER FUNCTIONS -----#
@mcp.tool
async def read_graph():
    """Read and print a user/LLM-friendly summary of the entire knowledge graph.

    Returns:
        User/LLM-friendly summary of the entire knowledge graph in text/markdown format
    """
    graph = await manager.read_graph()

    # Print user info
    lines: list[str] = ["💭 You remember the following information about the user:"]

    try:
        ui_print = await print_user_info(graph=graph)
        logger.debug(f"read_graph() ui_print: {ui_print}")
        lines.append(ui_print)
    except Exception as e:
        raise ToolError(f"Error while printing user info: {e}")

    # Print all entities from the graph
    try:
        lines.append(f"👤 You've made observations about {len(graph.entities)} entities:")
        ent_print = await print_entities(graph=graph)
        lines.append(ent_print)
    except Exception as e:
        raise ToolError(f"Error while printing entities: {e}")

    # Print relations to and from user
    try:
        user_relations = await manager.get_relations_from_id(
            entity_id=graph.user_info.linked_entity_id
        )
    except Exception as e:
        raise ToolError(f"Error getting relations from user entity: {e}")
    if user_relations:
        lines.append(
            f"🔗 You've learned about {len(user_relations)} relations between the user and these entities:"
        )
        lines.append(await print_relations(relations=user_relations))
    else:
        lines.append("(No relations found for user entity - this may be an error!)")

    # Supabase integration: Print email summaries
    if supabase_manager:
        try:
            email_summaries = await supabase_manager.get_email_summaries()
        except Exception as e:
            raise ToolError(f"(Supabase) Error while getting email summaries: {e}")
        if email_summaries:
            lines.append("")
            lines.append(
                f"📧 The user's got mail! Retrieved summaries for {len(email_summaries)} email messages:"
            )
            try:
                lines.append(
                    await print_email_summaries(
                        email_summaries,
                        options=PrintOptions(
                            ol=True,
                        ),
                    )
                )
            except Exception as e:
                raise ToolError(f"(Supabase) Error while printing email summaries: {e}")
        else:
            lines.append("")
            lines.append("📭 No new email summaries found! The user is all caught up!")
    else:
        logger.info(
            "(Supabase) Supabase integration is disabled, no email summaries will be printed"
        )

    # Remove any invalid lines (None types, etc.)
    for line in lines:
        if not isinstance(line, str):
            lines.remove(line)
            continue
    result = "\n".join(lines)

    asyncio.create_task(supabase_manager.mark_as_reviewed(email_summaries))
    return result


# ----- MAIN APPLICATION ENTRY POINT -----#


async def startup_check() -> None:
    """Check the startup of the server. Exits with an error if the server will not be able to start."""
    try:
        _ = await manager._load_graph()
    except Exception as e:
        raise ToolError(str(e))


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
        await startup_check()
        logger.info("✅ Startup check passed: memory file valid")
    except Exception as e:
        logger.error(f"🛑 Startup check failed: {e}")
        sys.exit(1)

    # Supabase integration: conditionally initialize if enabled and configured
    try:
        supabase_manager = SupabaseManager(settings.supabase)
        add_supabase_tools(mcp, supabase_manager)
        logger.info("☁️ Supabase integration enabled and initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Supabase integration: {e}")

    await mcp.run_async(transport=validated_transport, **transport_kwargs)


def run_sync():
    """Synchronus entry point for the server."""
    asyncio.run(start_server())


if __name__ == "__main__":
    asyncio.run(start_server())
