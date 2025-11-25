from typing import Any
from datetime import datetime, timezone

from supabase import create_client, Client as SBClient  # type: ignore

from .models import KnowledgeGraph, Entity, Observation, Relation, UserIdentifier, GraphMeta
from .iq_logging import logger
from .settings import SupabaseConfig


# Versioning for Supabase schema (tables/columns stored in Supabase)
# Bump when Supabase-side data model changes incompatibly.
SUPABASE_SCHEMA_VERSION: int = 1


class SupabaseException(Exception):
    """Exception raised for errors in the IQ-MCP Supabase integration."""

    pass


class EmailSummary:
    """Object representing an email summary from Supabase."""

    def __init__(
        self,
        message_id: str,
        thread_id: str,
        from_address: str,
        from_name: str,
        reply_to: str | None,
        timestamp: Any | None,
        subject: str,
        summary: str,
        links: list[dict[str, str]] | None,
    ) -> None:
        """Initialize an EmailSummary object."""
        self.message_id = message_id
        self.thread_id = thread_id
        self.from_address = from_address
        self.from_name = from_name
        self.reply_to = reply_to
        self.timestamp = timestamp
        self.subject = subject
        self.summary = summary
        self.links = links


class SupabaseManager:
    """Lightweight manager for optional Supabase integration.

    Pass in a SupabaseConfig object to configure the manager:
    - `url`: Supabase project URL
    - key: Supabase anon or service role key with read access
    - email_table (optional): Name of the table to query for email summaries (default: "emailSummaries")
    - entities_table (optional): Name of the table to query for entities (default: "kgEntities")
    - observations_table (optional): Name of the table to query for observations (default: "kgObservations")
    - relations_table (optional): Name of the table to query for relations (default: "kgRelations")
    - user_info_table (optional): Name of the table to query for user info (default: "kgUserInfo")
    """

    def __init__(self, config: SupabaseConfig) -> None:
        self.settings: SupabaseConfig = config
        self.client = create_client(self.settings.url, self.settings.key)

    def _ensure_client(self) -> SBClient:
        if not self.client:
            logger.error("IQ-MCP Supabase client not initialized, (re)initializing...")
            self.client = create_client(self.settings.url, self.settings.key)
        return self.client

    def get_schema_version(self) -> int:
        """Return the current Supabase schema version expected by this codebase."""
        return SUPABASE_SCHEMA_VERSION

    async def get_email_summaries(
        self,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        include_reviewed: bool = False,
    ) -> list[EmailSummary]:
        """Return email summaries from the Supabase integration.

        Returns:
            list[EmailSummary]: email summaries from the Supabase integration, optionally filtered by time and reviewed status.
        """
        try:
            client = self._ensure_client()
        except Exception as e:
            logger.error(f"(Supabase) Error initializing client: {e}")
            raise SupabaseException(f"(Supabase) Error initializing client: {e}")

        # If a time constraint is provided, convert to UTC and set to 00:00:00 (inclusive filtering)
        if from_date:
            from_ts = from_date.astimezone(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        else:
            from_ts = None

        # If a time constraint is provided, convert to UTC and set to 23:59:59 (inclusive filtering)
        if to_date:
            to_ts = to_date.astimezone(timezone.utc).replace(
                hour=23, minute=59, second=59, microsecond=999999
            )
        else:
            to_ts = None

        email_summary_table = self.settings.email_table
        logger.debug(f"(Supabase) Getting email summaries from table {email_summary_table}")
        logger.debug(f"(Supabase) From date: {from_ts}")
        logger.debug(f"(Supabase) To date: {to_ts}")
        logger.debug(f"(Supabase) Include reviewed: {include_reviewed}")

        # Get the supabase data

        query = client.table(email_summary_table).select("*")
        if not include_reviewed:
            query = query.eq("reviewed", "false")
        if from_ts:
            query = query.gte("received_at", from_ts)
        if to_ts:
            query = query.lte("received_at", to_ts)
        response = query.execute()

        summaries: list[EmailSummary] = []
        try:
            for row in response.data:
                summaries.append(
                    EmailSummary(
                        message_id=row.get("message_id"),
                        thread_id=row.get("thread_id"),
                        from_address=row.get("from_address"),
                        from_name=row.get("from_name"),
                        reply_to=row.get("reply_to"),
                        timestamp=row.get("received_at"),
                        subject=row.get("subject"),
                        summary=row.get("text_summary"),
                        links=row.get("links"),
                    )
                )
        except Exception as e:
            logger.error(f"(Supabase) Error parsing email summaries from Supabase: {e}")
            raise SupabaseException(f"(Supabase) Error parsing email summaries from Supabase: {e}")

        if not summaries:
            logger.error("(Supabase) Bad data returned from Supabase!")
            raise SupabaseException("(Supabase) Bad data returned from Supabase!")

        logger.info(
            f"📫 Retrieved {len(summaries)} email summaries from table {email_summary_table}!"
        )

        return summaries

    async def mark_as_reviewed(self, email_summaries: list[EmailSummary]) -> None:
        """Mark email summaries as reviewed in Supabase."""
        client = self._ensure_client()
        if self.settings.dry_run:
            logger.warning("(Supabase) 🏜️ Dry run mode enabled, skipping mark_as_reviewed()")
            return
        email_summary_table = self.settings.email_table
        try:
            email_ids = [message.message_id for message in email_summaries]
            _ = (
                client.table(email_summary_table)
                .update({"reviewed": "true"})
                .in_("message_id", email_ids)
                .execute()
            )
        except Exception as e:
            logger.error(f"(Supabase) Error marking email summaries as reviewed in Supabase: {e}")
        else:
            logger.info(
                f"(Supabase) Marked {len(email_ids)} email summaries as reviewed in Supabase"
            )

    async def save_knowledge_graph(self, graph: KnowledgeGraph) -> None:
        """
        Replace Supabase knowledge graph tables with a cleaned snapshot from the provided graph.

        Order of operations (to satisfy FK constraints):
        1) Delete relations, then observations, then entities
        2) Insert entities, then observations, then relations
        """
        if self.settings.dry_run:
            logger.warning("(Supabase) 🏜️ Dry run mode enabled, skipping sync_knowledge_graph()")
            return

        client = self._ensure_client()

        entities_table = self.settings.entities_table
        observations_table = self.settings.observations_table
        relations_table = self.settings.relations_table
        user_info_table = self.settings.user_info_table

        # --- Prepare cleaned records ---
        try:
            # Entities: dedupe by id, ensure core fields only
            entity_by_id: dict[str, Entity] = {}
            for e in graph.entities:
                if not e or not getattr(e, "id", None):
                    continue
                entity_by_id[str(e.id)] = e

            entities_payload: list[dict[str, Any]] = []
            for e in entity_by_id.values():
                aliases: list[str] = []
                try:
                    for a in e.aliases or []:
                        if isinstance(a, str) and a.strip():
                            aliases.append(a)
                except Exception:
                    pass
                ctime = str(getattr(e, "ctime", None))
                mtime = str(getattr(e, "mtime", None))

                entities_payload.append(
                    {
                        "id": str(e.id),
                        "name": e.name,
                        "type": e.entity_type,
                        "aliases": aliases,  # expects text[] in Supabase; adjust schema accordingly
                        "icon": getattr(e, "icon", None),
                        "created_at": ctime,
                        "modified_at": mtime,
                    }
                )

            # Observations: group per entity, dedupe by content
            observations_payload: list[dict[str, Any]] = []
            for e in entity_by_id.values():
                seen_contents: set[str] = set()
                for o in e.observations or []:
                    try:
                        content = (o.content or "").strip()
                        if not content or content in seen_contents:
                            continue
                        seen_contents.add(content)
                        ts = str(o.timestamp)
                        durability = getattr(o, "durability", None)
                        durability_str = getattr(durability, "value", None) or str(durability)
                        observations_payload.append(
                            {
                                "linked_entity": str(e.id),
                                "content": content,
                                "durability": durability_str,
                                "created_at": ts,
                            }
                        )
                    except Exception as ex:
                        logger.error(f"Error preparing observation for entity {e.name}: {ex}")
                        continue

            # Relations: dedupe by (from_id, to_id, relation) and keep only those whose endpoints exist
            rel_key_seen: set[tuple[str, str, str]] = set()
            relations_payload: list[dict[str, Any]] = []
            valid_ids = set(entity_by_id.keys())
            for r in graph.relations or []:
                try:
                    from_id = str(getattr(r, "from_id", "") or getattr(r, "from_entity_id", ""))
                    to_id = str(getattr(r, "to_id", "") or getattr(r, "to_entity_id", ""))
                    relation = (r.relation or "").strip()
                    if not from_id or not to_id or not relation:
                        continue
                    if from_id not in valid_ids or to_id not in valid_ids:
                        continue
                    key = (from_id, to_id, relation)
                    if key in rel_key_seen:
                        continue
                    rel_key_seen.add(key)
                    relations_payload.append(
                        {
                            "from": from_id,
                            "to": to_id,
                            "content": relation,
                        }
                    )
                except Exception as ex:
                    logger.error(f"Error preparing relation: {ex}")
                    continue
        except Exception as e:
            logger.error(f"Error preparing Supabase payloads: {e}")
            raise SupabaseException(f"Error preparing Supabase payloads: {e}")

        # User info
        user_info_payload: list[dict[str, Any]] = []
        if graph.user_info:
            user_info_payload.append(
                {
                    "linked_entity_id": str(graph.user_info.linked_entity_id),
                    "preferred_name": graph.user_info.preferred_name,
                    "first_name": graph.user_info.first_name,
                    "last_name": graph.user_info.last_name,
                    "middle_names": graph.user_info.middle_names,
                    "pronouns": graph.user_info.pronouns,
                    "nickname": graph.user_info.nickname,
                    "prefixes": graph.user_info.prefixes,
                    "suffixes": graph.user_info.suffixes,
                    "emails": graph.user_info.emails,
                    "base_name": graph.user_info.base_name,
                    "names": graph.user_info.names,
                }
            )
        else:
            raise RuntimeError("User info not found in graph! WTF?")

        # --- Replace remote data ---
        # Delete in FK-safe order: relations -> observations -> entities
        try:
            _ = client.table(relations_table).delete().neq("from", "").execute()
            _ = client.table(observations_table).delete().neq("linked_entity", "").execute()
            _ = client.table(entities_table).delete().neq("id", "").execute()
            _ = client.table(user_info_table).delete().neq("first_name", "").execute()
        except Exception as e:
            logger.error(f"Error clearing Supabase tables: {e}")
            raise SupabaseException(f"Error clearing Supabase tables: {e}")

        # Insert payloads: entities -> observations -> relations
        try:
            if entities_payload:
                _ = client.table(entities_table).insert(entities_payload).execute()
            if observations_payload:
                # Optional: chunk if very large; current volume expected manageable
                _ = client.table(observations_table).insert(observations_payload).execute()
            if relations_payload:
                _ = client.table(relations_table).insert(relations_payload).execute()
            if user_info_payload:
                _ = client.table(user_info_table).insert(user_info_payload).execute()
        except Exception as e:
            logger.error(f"Error inserting Supabase data: {e}")
            raise SupabaseException(f"Error inserting Supabase data: {e}")

        logger.info(
            f"Supabase sync complete: entities={len(entities_payload)}, observations={len(observations_payload)}, relations={len(relations_payload)}"
        )
        return "🔃 Successfully synced knowledge graph to Supabase!"

    async def get_knowledge_graph(self) -> KnowledgeGraph:
        """Get the knowledge graph from Supabase."""
        client = self._ensure_client()
        entities_table = self.settings.entities_table
        observations_table = self.settings.observations_table
        relations_table = self.settings.relations_table
        user_info_table = self.settings.user_info_table

        try:
            entities_response = client.table(entities_table).select("*").execute()
            observations_response = client.table(observations_table).select("*").execute()
            relations_response = client.table(relations_table).select("*").execute()
            user_info_response = client.table(user_info_table).select("*").execute()
        except Exception as e:
            logger.error(f"Error loading knowledge graph from Supabase: {e}")
            raise SupabaseException(f"Error loading knowledge graph from Supabase: {e}")
        logger.debug("(Supabase) Responses OK")

        entities: list[Entity] = []
        observations: dict[str, list[Observation]] = {}
        relations: list[Relation] = []
        user_info: UserIdentifier | None = None
        try:
            for row in observations_response.data:
                o = Observation.from_values(
                    content=row.get("content"),
                    durability=row.get("durability"),
                    timestamp=row.get("created_at"),
                )
                if row.get("linked_entity") not in observations:
                    observations[row.get("linked_entity")] = []
                observations[row.get("linked_entity")].append(o)
        except Exception as e:
            logger.error(f"Error parsing observations from Supabase: {e}")
            raise SupabaseException(f"Error parsing observations from Supabase: {e}")
        try:
            for row in entities_response.data:
                e_id = row.get("id")
                if e_id not in observations:
                    logger.warning(f"No observations found for entity `{e_id}` in Supabase!")
                    e_obs = []
                else:
                    e_obs = observations[e_id]

                e = Entity.from_values(
                    id=row.get("id"),
                    name=row.get("name"),
                    entity_type=row.get("type"),
                    aliases=row.get("aliases"),
                    icon=row.get("icon"),
                    ctime=row.get("created_at"),
                    mtime=row.get("modified_at"),
                    observations=e_obs,
                )
                entities.append(e)
        except Exception as e:
            logger.error(f"Error parsing entities from Supabase: {e}")
            raise SupabaseException(f"Error parsing entities from Supabase: {e}")
        try:
            for row in relations_response.data:
                r = Relation.from_values(
                    from_id=row.get("from"),
                    to_id=row.get("to"),
                    relation=row.get("content"),
                    ctime=row.get("created_at"),
                )
                relations.append(r)
        except Exception as e:
            logger.error(f"Error parsing relations from Supabase: {e}")
            raise SupabaseException(f"Error parsing relations from Supabase: {e}")
        try:
            for row in user_info_response.data:
                ui = UserIdentifier.from_values(
                    preferred_name=row.get("preferred_name"),
                    first_name=row.get("first_name"),
                    last_name=row.get("last_name"),
                    middle_names=row.get("middle_names"),
                    pronouns=row.get("pronouns"),
                    nickname=row.get("nickname"),
                    prefixes=row.get("prefixes"),
                    suffixes=row.get("suffixes"),
                    emails=row.get("emails"),
                    linked_entity_id=row.get("linked_entity_id"),
                )
                user_info = ui
        except Exception as e:
            logger.error(f"Error parsing user info from Supabase: {e}")
            raise SupabaseException(f"Error parsing user info from Supabase: {e}")
        try:
            graph = KnowledgeGraph.from_components(
                user_info=user_info,
                entities=entities,
                relations=relations,
                meta=GraphMeta(),  # TODO: Add metadata from Supabase
            )
        except Exception as e:
            logger.error(f"Error constructing knowledge graph from Supabase: {e}")
            raise SupabaseException(f"Error constructing knowledge graph from Supabase: {e}")
        try:
            graph.validate()
        except Exception as e:
            logger.error(f"Error validating knowledge graph from Supabase: {e}")
            raise SupabaseException(f"Error validating knowledge graph from Supabase: {e}")

        return graph


# async def DEBUG_test_IQ_SUPABASE_init() -> None:
#     """Debug test for the Supabase integration."""
#     try:
#         summaries = await supabase.get_email_summaries()
#         logger.info(f"Retrieved {len(summaries)} email summaries from Supabase")
#     except Exception as e:
#         logger.error(f"Error getting email summaries from Supabase: {e}")
#         raise SupabaseException(f"Error getting email summaries from Supabase: {e}")


__all__ = ["EmailSummary", "SupabaseManager", "SupabaseException", "SUPABASE_SCHEMA_VERSION"]
