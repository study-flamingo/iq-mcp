from dataclasses import dataclass
from typing import Any, Optional
from dotenv import load_dotenv
from .settings import supabase_settings, Logger as logger, SupabaseSettings

load_dotenv()


@dataclass
class EmailSummary:
    """Object representing an email summary from Supabase."""

    id: str
    from_address: str
    from_name: str
    reply_to: str | None
    timestamp: Any | None
    subject: str
    summary: str
    links: list[dict[str, Any]] | None


class SupabaseManager:
    """Lightweight manager for optional Supabase integration.

    - Pure configuration is provided via SupabaseSettings
    - Client is created lazily the first time it is needed
    - If configuration or library is missing, integration is disabled
    """

    def __init__(self, settings_obj: SupabaseSettings | None) -> None:
        self._settings: SupabaseSettings | None = settings_obj
        self._client = None  # created lazily

    @property
    def enabled(self) -> bool:
        return self._settings is not None

    def _ensure_client(self):
        if not self.enabled:
            raise RuntimeError("Supabase integration is not configured")
        if self._client is None:
            try:
                import supabase as sb  # lazy import to avoid hard dependency
            except ImportError as e:
                raise RuntimeError(
                    "Supabase library is not installed. Install with 'uv pip install supabase'"
                ) from e
            self._client = sb.create_client(self._settings.url, self._settings.key)  # type: ignore[union-attr]
        return self._client

    async def get_new_email_summaries(self) -> list[EmailSummary]:
        """Return unreviewed email summaries.

        Returns:
            list[EmailSummary]: summaries with reviewed == false (if column exists); otherwise all rows.
        """
        client = self._ensure_client()
        table_name = self._settings.email_table  # type: ignore[union-attr]
        try:
            # Try to filter by reviewed == false if available
            query = client.table(table_name).select("*")
            try:
                query = query.eq("reviewed", False)
            except Exception:
                pass
            logger.debug(f"Querying Supabase for new email summaries from '{table_name}'")
            response = await query.execute()
            data = getattr(response, "data", None)
            if not isinstance(data, list):
                raise RuntimeError("Unexpected response format from Supabase")

            summaries: list[EmailSummary] = []
            for row in data:
                summaries.append(
                    EmailSummary(
                        id=row.get("id") or row.get("message_id"),
                        from_address=row.get("from_address", ""),
                        from_name=row.get("from_name", ""),
                        reply_to=row.get("reply_to"),
                        timestamp=row.get("timestamp"),
                        subject=row.get("subject", ""),
                        summary=row.get("summary", ""),
                        links=row.get("links") or [],
                    )
                )
            return summaries
        except Exception as e:
            logger.error(f"Error querying Supabase: {e}")
            raise


# Export a singleton manager configured from global settings
supabase = SupabaseManager(supabase_settings)

__all__ = ["supabase", "EmailSummary", "SupabaseSettings", "SupabaseManager"]
