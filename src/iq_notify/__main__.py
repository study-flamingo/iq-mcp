import json
import os
import sys
from typing import Any

from . import get_unreviewed_email_summaries


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]

    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
    table_name = os.environ.get("IQ_NOTIFY_TABLE", "emailSummaries")
    schema_name = os.environ.get("IQ_NOTIFY_SCHEMA")

    if not supabase_url or not supabase_key:
        print("Missing SUPABASE_URL or SUPABASE_KEY/ANON/SERVICE env vars", file=sys.stderr)
        return 2

    try:
        rows = get_unreviewed_email_summaries(
            supabase_url=supabase_url,
            supabase_key=supabase_key,
            table_name=table_name,
            schema_name=schema_name,
        )
    except Exception as exc:  # Provide a clear error to the caller
        print(f"Error querying Supabase: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(rows, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
