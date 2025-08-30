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
from dataclasses import dataclass
import argparse
import os
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv


logging.basicConfig(level=logging.INFO)

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


@dataclass
class SupabaseSettings:
    """Supabase settings for the IQ-MCP server.

    Attributes:
        url: Supabase project URL
        key: Supabase anon or service role key with read access
        email_table: Name of the table to query for email summaries
        entities_table: Name of the table to query for entities
        relations_table: Name of the table to query for relations
        user_table: Name of the table to query for user info
    """

    url: str
    key: str
    email_table: str | None = None
    entities_table: str | None = None
    relations_table: str | None = None
    user_table: str | None = None

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
        self.supabase_settings = supabase_settings

    # ---------- Construction ----------
    @classmethod
    def load(cls) -> "IQSettings":
        """
        Create a IQ-MCP Settings instance from CLI args, env, and defaults.
        
        Properties:
            debug (bool): Enables verbose logging when True
            transport (Transport enum): Validated transport value ("stdio" | "sse" | "http")
            port (int): Server port (used when transport is http)
            streamable_http_host (str): Optional HTTP host
            streamable_http_path (str): Optional HTTP path
            memory_path (Path): Absolute path to memory JSONL file
            project_root (Path): Resolved project root path
            no_emojis (bool): Disable emojis in the output
            supabase_settings (SupabaseSettings): Supabase settings
        """
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

        # Initialize logger
        logger = logging.getLogger("iq-mcp")

        # Debug mode
        debug: bool = args.debug or os.environ.get("IQ_DEBUG", "false").lower() == "true"
        if debug:
            # If debug is set, set the environment variable to true for other scripts to use
            os.environ["IQ_DEBUG"] = "true"
            logger.setLevel(logging.DEBUG)
            logger.debug(f"🐞 Debug mode: {debug}")

        # Load .env if available
        env_path = os.getenv("IQ_ENV_PATH")

        if env_path and Path(env_path).exists():
            load_dotenv(env_path, verbose=False)
            logger.debug(f"Loaded .env from {env_path}")
        elif load_dotenv(verbose=False):
            logger.debug("Loaded .env from current directory")
        elif load_dotenv(DEFAULT_MEMORY_PATH):
            logger.debug(f"Loaded .env from default memory path: {DEFAULT_MEMORY_PATH}")

        # Resolve project root (repo root)
        project_root: Path = Path(__file__).parents[2].resolve()

        # Transport
        transport_raw = (args.transport or os.getenv("IQ_TRANSPORT", "stdio")).strip().lower()
        if transport_raw not in TRANSPORT_ENUM:
            valid = ", ".join(sorted({"stdio", "sse", "streamable-http", "http"}))
            raise ValueError(f"Invalid transport '{transport_raw}'. Valid options: {valid}")
        transport: Transport = TRANSPORT_ENUM[transport_raw]

        # Port/Host/Path for HTTP
        http_port = int(args.port) or os.environ.get("IQ_STREAMABLE_HTTP_PORT", DEFAULT_PORT)
        http_host = args.http_host or os.getenv("IQ_STREAMABLE_HTTP_HOST")
        http_path = args.http_path or os.getenv("IQ_STREAMABLE_HTTP_PATH")

        # Memory path precedence: CLI > env > default(project_root/memory.jsonl) > example.jsonl

        memory_path_input = args.memory_path or os.getenv("IQ_MEMORY_PATH", DEFAULT_MEMORY_PATH)
        memory_path = Path(memory_path_input).resolve()

        # Disable emojis if desired
        no_emojis = args.no_emojis or os.getenv("IQ_NO_EMOJIS", "false").lower() == "true"

        # Supabase integration (pure configuration only; no clients created here)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        supabase_email_table = os.getenv("SUPABASE_EMAIL_TABLE")
        supabase_entities_table = os.getenv("SUPABASE_ENTITIES_TABLE")
        supabase_relations_table = os.getenv("SUPABASE_RELATIONS_TABLE")
        supabase_user_table = os.getenv("SUPABASE_USER_TABLE")
        
        # If no URL or key, skip Supabase configuration entirely
        if not supabase_url or not supabase_key:
            logger.warning("⚠️ No Supabase settings provided, skipping Supabase integration.")
            supabase_settings = None
        else:
            # Fill in defaults if only URL and key are provided
            supabase_email_table = supabase_email_table or "emailSummaries"
            if not supabase_entities_table:
                logger.warning("⚠️ No entity table name provided, defaulting to 'iqEntities'")
                supabase_entities_table = "iqEntities"
            if not supabase_relations_table:
                logger.warning("⚠️ No relation table name provided, defaulting to 'iqRelations'")
                supabase_relations_table = "iqRelations"
            if not supabase_user_table:
                logger.warning("⚠️ No user table name provided, defaulting to 'iqUsers'")
                supabase_user_table = "iqUsers"

            supabase_settings = SupabaseSettings(
                url=supabase_url,
                key=supabase_key,
                email_table=supabase_email_table,
                entities_table=supabase_entities_table,
                relations_table=supabase_relations_table,
                user_table=supabase_user_table,
            )

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

    def get_logger(self) -> logging.Logger:
        """Get the logger for the IQ-MCP server, configured by the settings object."""
        logging.basicConfig(level=logging.DEBUG if self.debug else logging.INFO)
        logger = logging.getLogger("iq-mcp")
        logger.debug("Retrieved debug logger")
        return logger


Settings = IQSettings.load()
Logger = Settings.get_logger()
supabase_settings: SupabaseSettings | None = Settings.supabase_settings
