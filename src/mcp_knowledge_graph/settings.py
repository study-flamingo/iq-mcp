"""
Centralized configuration for the IQ-MCP server.

This module consolidates all configuration concerns (CLI args, environment
variables, and sensible defaults) into a single, validated settings object.

Precedence (highest first):
- CLI arguments
- Environment variables (optionally from .env)
- Defaults
"""

from __future__ import annotations

import logging
import argparse
import os
from pathlib import Path
from typing import Literal

from .notify import SupabaseSettings

logger = logging.getLogger("iq-mcp")


# Optionally load .env if available
try:
    from dotenv import load_dotenv
except Exception: 
    load_dotenv = None

DEFAULT_MEMORY_PATH = Path(__name__).parent.parent / "memory.jsonl"
DEFAULT_PORT = 8000


Transport = Literal["stdio", "sse", "http"]

TRANSPORT_ENUM: dict[str, Transport] = {
    "stdio": "stdio",
    "http": "http",
    "sse": "sse",
    # Common aliases that normalize to http
    "streamable-http": "http",
    "streamablehttp": "http",
    "streamable_http": "http",
    "streamable http": "http",
    "streamableHttp": "http",
}



class IQSettings:
    """IQ-MCP Application settings loaded from CLI and environment.

    Attributes:
        debug: Enables verbose logging when True
        transport: Validated transport value ("stdio" | "sse" | "http")
        port: Server port (used when transport is http)
        streamable_http_host: Optional HTTP host
        streamable_http_path: Optional HTTP path
        memory_path: Absolute path to memory JSONL file
        project_root: Resolved project root path
        no_emojis: Disable emojis in the output
        supabase_url: Supabase project URL
        supabase_key: Supabase anon or service role key with read access
        supabase_table: Name of the table to query
    """

    def __init__(
        self,
        *,
        debug: bool,
        transport: Transport,
        port: int,
        memory_path: str,
        streamable_http_host: str | None,
        streamable_http_path: str | None,
        project_root: Path,
        no_emojis: bool,
        supabase_settings: SupabaseSettings | None,
    ) -> None:
        self.debug = bool(debug)
        self.transport = transport
        self.memory_path = memory_path
        self.port = int(port)
        self.streamable_http_host = streamable_http_host
        self.streamable_http_path = streamable_http_path
        self.project_root = project_root
        self.no_emojis = no_emojis
        self.supabase = supabase_settings

    # ---------- Construction ----------
    @classmethod
    def load(cls) -> "IQSettings":
        """Create a Settings instance from CLI args, env, and defaults.

        Precedence: CLI > env > defaults
        """
        # Load .env if available
        env_path = os.getenv("IQ_ENV_PATH")
        if load_dotenv:
            if env_path and Path(env_path).exists():
                load_dotenv(env_path, verbose=False)
            else:
                load_dotenv(verbose=False)

        # CLI args > Env vars > Defaults
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--memory-path", type=str)
        parser.add_argument("--debug", action="store_true", default=None)
        parser.add_argument("--transport", type=str)
        parser.add_argument("--port", type=int, default=DEFAULT_PORT)
        parser.add_argument("--http-host", type=str)
        parser.add_argument("--http-path", type=str)
        parser.add_argument("--no-emojis", action="store_true", default=None)
        args, _ = parser.parse_known_args()

        # Resolve project root (repo root)
        project_root: Path = Path(__file__).resolve().parents[2]

        # Debug
        debug: bool = args.debug or os.environ.get("IQ_DEBUG", "false").lower() == "true"

        # Transport
        transport_raw = (args.transport or os.getenv("IQ_TRANSPORT", "stdio")).strip().lower()
        if transport_raw not in TRANSPORT_ENUM:
            valid = ", ".join(sorted({"stdio", "sse", "streamable-http", "http"}))
            raise ValueError(f"Invalid transport '{transport_raw}'. Valid options: {valid}")
        transport: Transport = TRANSPORT_ENUM[transport_raw]

        # Port/Host/Path for HTTP
        http_port = (int(args.port) or os.environ.get("IQ_STREAMABLE_HTTP_PORT", DEFAULT_PORT))
        http_host = args.http_host or os.getenv("IQ_STREAMABLE_HTTP_HOST")
        http_path = args.http_path or os.getenv("IQ_STREAMABLE_HTTP_PATH")

        # Memory path precedence: CLI > env > default(project_root/memory.jsonl) > example.jsonl

        memory_path_input = args.memory_path or os.getenv("IQ_MEMORY_PATH", DEFAULT_MEMORY_PATH)
        memory_path = Path(memory_path_input).resolve()

        # Supabase, if notifications are enabled (optional)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        supabase_table = os.getenv("SUPABASE_TABLE")
        if supabase_url and supabase_key and supabase_table:
            supabase_settings = SupabaseSettings(
                url=supabase_url,
                key=supabase_key,
                table=supabase_table,
            )
        else:
            logger.warning("⚠️ No Supabase settings provided. Notifications will not be enabled.")
            supabase_settings = None

        # Disable emojis if desired
        no_emojis = args.no_emojis or os.getenv("IQ_NO_EMOJIS", "false").lower() == "true"


        return cls(
            debug=debug,
            transport=transport,
            port=http_port,
            streamable_http_host=http_host,
            streamable_http_path=http_path,
            memory_path=memory_path,
            project_root=project_root,
            supabase_settings=supabase_settings,
            no_emojis=no_emojis,
        )

    # ---------- Helpers ----------
    @staticmethod
    def _resolve_memory_path(project_root: Path, path_str: str) -> Path:
        candidate = Path(path_str)
        if candidate.is_absolute():
            return candidate
        return project_root / candidate


settings = IQSettings.load()
