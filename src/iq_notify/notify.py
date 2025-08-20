import json
import os
import sys
import asyncio
from typing import Any
from pydantic import BaseModel
from supabase import create_client, Client

from . import get_unreviewed_email_summaries

class EmailSummary(BaseModel):
    """Object representing an email summary from Supabase."""
    message_id: str
    thread_id: str
    from_address: str
    from_name: str
    reply_to: str
    subject: str
    summary: str
    links: list[dict[str, Any]]

class SupabaseClient(BaseModel):
    """A single-purpose client for the Supabase database. Returns new email summaries that have not been reviewed.
    
    Args:
        supabase_url: Supabase project URL (can be set in env vars)
        supabase_key: Supabase anon or service role key with read access (can be set in env vars)
        supabase_table: Name of the table to query. Defaults to "emailSummaries".
    
    Args can also be set with env vars:
        - SUPABASE_URL=<url>
        - SUPABASE_KEY=<key>
        - SUPABASE_TABLE=<table>
    """
    def __init__(self, supabase_url: str, supabase_key: str, supabase_table: str = "emailSummaries"):
        if not supabase_url or not supabase_key:
            supabase_url = os.environ.get("SUPABASE_URL")
            supabase_key = os.environ.get("SUPABASE_KEY")
            if not supabase_url or not supabase_key:
                raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY env vars!")

        self._supabase_url = supabase_url
        self._supabase_key = supabase_key
        self._supabase_table = supabase_table
        self.client = self._get_client()
        
    def _get_client(self) -> Client:
        if not self.client:
            # If client is missing for some reason, create it
            self.client = create_client(self._supabase_url, self._supabase_key)
        return self.client

    async def get_new_email_summaries(self) -> list[EmailSummary]:
        """Return rows from Supabase where reviewed == false, optionally filtered by context.

        Returns
        - List of summarized email objects (EmailSummary objects).
        """

        query = self.client.table(self._supabase_table).select("*").eq("reviewed", False)

        try:
            response = await query.execute()
            
            # supabase-py 2.x returns an object with .data attribute
            data = getattr(response, "data")
            if isinstance(data, list):
                new_email_summaries = [EmailSummary(**row) for row in data]
            else:
                raise RuntimeError("Unexpected response format from Supabase")

            return new_email_summaries

        except Exception as e:
            print(f"Error querying Supabase: {e}")

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
table = os.environ.get("SUPABASE_TABLE")

supabase = SupabaseClient(supabase_url, supabase_key, supabase_table)

__all__ = [
    "supabase",
    "EmailSummary",
]
