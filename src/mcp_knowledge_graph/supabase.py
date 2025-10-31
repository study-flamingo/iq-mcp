import logging
import os
from dataclasses import dataclass
from typing import Any
from dotenv import load_dotenv
from datetime import datetime, timezone

from supabase import create_client, Client as SBClient

from .models import KnowledgeGraph, Entity
from .logging import get_iq_mcp_logger

load_dotenv()

logger = get_iq_mcp_logger()


class SupabaseException(Exception):
    """Exception raised for errors in the IQ-MCP Supabase integration."""
    pass


class SupabaseSettings:
    """Supabase settings for the IQ-MCP server.

    Attributes:
        `url`: Supabase project URL
        `key`: Supabase anon or service role key with read access
        `email_table` (optional): Name of the table to query for email summaries (default: "emailSummaries")
        `entities_table` (optional): Name of the table to query for entities (default: "kgEntities")
        `observations_table` (optional): Name of the table to query for observations (default: "kgObservations")
        `relations_table` (optional): Name of the table to query for relations (default: "kgRelations")
    """

    def __init__(
        self,
        url: str,
        key: str,
        email_table: str | None = None,
        entities_table: str | None = None,
        observations_table: str | None = None,
        relations_table: str | None = None,
        dry_run: bool = False,
    ) -> None:
        self.url = url
        self.key = key
        self.email_table = email_table or os.getenv("IQ_SUPABASE_EMAIL_TABLE", "emailSummaries")
        self.entities_table = entities_table or os.getenv("IQ_SUPABASE_ENTITIES_TABLE", "kgEntities")
        self.observations_table = observations_table or os.getenv(
            "IQ_SUPABASE_OBSERVATIONS_TABLE", "kgObservations"
        )
        self.relations_table = relations_table or os.getenv(
            "IQ_SUPABASE_RELATIONS_TABLE", "kgRelations"
        )
        self.dry_run = dry_run

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

    Pass in a SupabaseSettings object to configure the manager:
    - `url`: Supabase project URL
    - key: Supabase anon or service role key with read access
    - email_table (optional): Name of the table to query for email summaries (default: "emailSummaries")
    - entities_table (optional): Name of the table to query for entities (default: "kgEntities")
    - observations_table (optional): Name of the table to query for observations (default: "kgObservations")
    - relations_table (optional): Name of the table to query for relations (default: "kgRelations")
    """

    def __init__(self, settings_obj: SupabaseSettings) -> None:
        self.settings: SupabaseSettings = settings_obj
        self.client = create_client(self.settings.url, self.settings.key)

    def _ensure_client(self) -> SBClient:
        if not self.client:
            logger.error("IQ-MCP Supabase client not initialized, (re)initializing...")
            self.client = create_client(self.settings.url, self.settings.key)
        return self.client

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
        client = self._ensure_client()

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

        # Get the supabase data

        try:
            query = client.table(email_summary_table).select("*")
            if not include_reviewed:
                query = query.eq("reviewed", "false")
            if from_ts:
                query = query.gte("received_at", from_ts)
            if to_ts:
                query = query.lte("received_at", to_ts)
            response = query.execute()
        except Exception as e:
            logger.error(f"Error getting email summaries from Supabase: {e}")
            raise SupabaseException(f"Error getting email summaries from Supabase: {e}")

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
            logger.error(f"Error parsing email summaries from Supabase: {e}")
            raise SupabaseException(f"Error parsing email summaries from Supabase: {e}")

        logger.info(f"📫 Retrieved {len(summaries)} email summaries from table {email_summary_table}!")

        return summaries

    async def mark_as_reviewed(self, email_summaries: list[EmailSummary]) -> None:
        """Mark email summaries as reviewed in Supabase."""
        client = self._ensure_client()
        email_summary_table = self.settings.email_table
        try:
            for summary in email_summaries:
                _ = (
                    client.table(email_summary_table)
                    .update({"reviewed": "true"})
                    .eq("message_id", summary.message_id)
                    .execute()
                )
        except Exception as e:
            logger.error(f"Error marking email summaries as read in Supabase: {e}")
        else:
            logger.info(f"Marked {len(email_summaries)} email summaries as read in Supabase")

    async def sync_knowledge_graph(self, graph: KnowledgeGraph) -> None:
        """
        Replace Supabase knowledge graph tables with a cleaned snapshot from the provided graph.

        Order of operations (to satisfy FK constraints):
        1) Delete relations, then observations, then entities
        2) Insert entities, then observations, then relations
        """
        if self.settings.dry_run:
            logger.warning("Dry run mode enabled, skipping sync")
            return
        
        client = self._ensure_client()

        entities_table = self.settings.entities_table
        observations_table = self.settings.observations_table
        relations_table = self.settings.relations_table

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

                entities_payload.append(
                    {
                        "id": str(e.id),
                        "name": e.name,
                        "entity_type": e.entity_type,
                        "aliases": aliases,  # expects text[] in Supabase; adjust schema accordingly
                        "icon": getattr(e, "icon", None),
                        "ctime": getattr(e, "ctime", None),
                        "mtime": getattr(e, "mtime", None),
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
                        ts = o.timestamp
                        ts_iso = (
                            ts.isoformat() if isinstance(ts, datetime) else str(ts) if ts else None
                        )
                        durability = getattr(o, "durability", None)
                        durability_str = getattr(durability, "value", None) or str(durability)
                        observations_payload.append(
                            {
                                "linked_entity": str(e.id),
                                "content": content,
                                "durability": durability_str,
                                "timestamp": ts_iso,
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
                            "from_id": from_id,
                            "to_id": to_id,
                            "relation": relation,
                        }
                    )
                except Exception as ex:
                    logger.error(f"Error preparing relation: {ex}")
                    continue
        except Exception as e:
            logger.error(f"Error preparing Supabase payloads: {e}")
            raise SupabaseException(f"Error preparing Supabase payloads: {e}")

        # --- Replace remote data ---
        # Delete in FK-safe order: relations -> observations -> entities
        try:
            _ = client.table(relations_table).delete().neq("from_id", "").execute()
            _ = client.table(observations_table).delete().neq("linked_entity", "").execute()
            _ = client.table(entities_table).delete().neq("id", "").execute()
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
        except Exception as e:
            logger.error(f"Error inserting Supabase data: {e}")
            raise SupabaseException(f"Error inserting Supabase data: {e}")

        logger.info(
            f"Supabase sync complete: entities={len(entities_payload)}, observations={len(observations_payload)}, relations={len(relations_payload)}"
        )


# async def DEBUG_test_IQ_SUPABASE_init() -> None:
#     """Debug test for the Supabase integration."""
#     try:
#         summaries = await supabase.get_email_summaries()
#         logger.info(f"Retrieved {len(summaries)} email summaries from Supabase")
#     except Exception as e:
#         logger.error(f"Error getting email summaries from Supabase: {e}")
#         raise SupabaseException(f"Error getting email summaries from Supabase: {e}")


__all__ = ["EmailSummary", "SupabaseSettings", "SupabaseManager", "SupabaseException"]
