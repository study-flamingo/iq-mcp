from typing import Any, Dict, List, Optional

__all__ = [
    "get_unreviewed_email_summaries",
]


def get_unreviewed_email_summaries(
    *,
    supabase_url: str,
    supabase_key: str,
    table_name: str = "emailSummaries",
    schema_name: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return rows from Supabase where reviewed == false, optionally filtered by context.

    Parameters
    ----------
    supabase_url: Supabase project URL.
    supabase_key: Supabase anon or service role key with read access.
    table_name: Name of the table to query. Defaults to "emailSummaries".
    schema_name: Optional Postgres schema name. Defaults to Supabase's default schema.

    Returns
    -------
    List of row dictionaries.
    """
    try:
        from supabase import create_client
    except Exception as import_error:  # pragma: no cover - clear message for missing dep
        raise RuntimeError(
            "Missing dependency 'supabase'. Install with: uv pip install -e . -g notify or pip install supabase"
        ) from import_error

    client = create_client(supabase_url, supabase_key)

    query_builder = client
    if schema_name:
        # supabase-py exposes PostgREST schema selection through client.postgrest.schema
        # Using public API where available
        try:
            query_builder = client.postgrest.schema(schema_name)  # type: ignore[attr-defined]
        except Exception:
            # Fallback: if schema handling differs, default to base client
            query_builder = client

    query = query_builder.table(table_name).select("*").eq("reviewed", False)

    response = query.execute()
    # supabase-py 2.x returns an object with .data attribute
    data = getattr(response, "data", response)
    if not isinstance(data, list):
        raise RuntimeError("Unexpected response format from Supabase")
    return data
