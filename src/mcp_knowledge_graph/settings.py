"""
Centralized configuration for the IQ-MCP server.

This module consolidates all configuration concerns (CLI args, environment
variables, and sensible defaults) into a single, validated settings object.

Architecture:
- IQSettings: Core application settings (always loaded)
- SupabaseConfig: Optional Supabase integration settings (loaded if enabled)
- AppSettings: Composition class that combines core + optional integrations

Precedence (highest first):
- CLI arguments
- Environment variables (optionally from .env)
- Defaults
"""

from __future__ import annotations

from dotenv import load_dotenv
import argparse
import os
from pathlib import Path
from typing import Literal
import logging as lg

from .version import IQ_MCP_VERSION, IQ_MCP_SCHEMA_VERSION

logger = lg.getLogger("iq-mcp-bootstrap")
logger.addHandler(lg.FileHandler(Path(__file__).parents[2].resolve() / "iq-mcp-bootstrap.log"))
logger.setLevel(lg.DEBUG)
logger.debug("Bootstrap logger set to debug")

# Default memory file at repo root
DEFAULT_MEMORY_PATH = Path(__file__).parents[2].resolve() / "memory.jsonl"
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
    """Core IQ-MCP application settings (transport, memory, logging, etc.).
    Attributes:
        `debug`: Enables verbose logging when True
        `transport`: Validated transport value ("stdio" | "sse" | "http")
        `port`: Server port (used when transport is http)
        `streamable_http_host`: Optional HTTP host
        `streamable_http_path`: Optional HTTP path
        `memory_path`: Absolute path to memory JSONL file
        `project_root`: Resolved project root path
        `no_emojis`: Disable emojis in the output
        `dry_run`: Enable dry-run mode (doesn't save anything)
        `enable_supabase`: Enable Supabase integration
    This class contains only the core settings required for the MCP server to function.
    Optional integrations are handled separately via integration-specific config classes.
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
        dry_run: bool,
        stateless_http: bool,
    ) -> None:
        self.debug = bool(debug)
        self.transport = transport
        self.memory_path = memory_path
        self.port = int(port)
        self.streamable_http_host = streamable_http_host
        self.streamable_http_path = streamable_http_path
        self.project_root = project_root
        self.no_emojis = no_emojis
        self.dry_run = dry_run
        self.stateless_http = stateless_http

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
            dry_run (bool): Enable dry-run mode
        """
        # CLI args > Env vars > Defaults
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--memory-path", type=str)
        parser.add_argument("--debug", action="store_true", default=None)
        parser.add_argument("--transport", type=str)
        parser.add_argument("--port", type=int, default=None)
        parser.add_argument("--http-host", type=str)
        parser.add_argument("--http-path", type=str)
        parser.add_argument("--no-emojis", action="store_true", default=None)
        parser.add_argument("--dry-run", action="store_true", default=False)
        # Supabase args are parsed separately in SupabaseConfig.load()
        parser.add_argument("--enable-supabase", action="store_true", default=None)
        parser.add_argument("--supabase-url", type=str, default=None)
        parser.add_argument("--supabase-key", type=str, default=None)
        args, _ = parser.parse_known_args()

        # Debug mode
        debug: bool = args.debug or os.environ.get("IQ_DEBUG", "false").lower() == "true"
        if debug:
            # If debug is set, set the environment variable to true for other scripts to use
            os.environ["IQ_DEBUG"] = "true"
            logger.setLevel(lg.DEBUG)
            logger.debug(f"🐞 Debug mode: {debug}")

        # Load .env if available
        env_path = os.getenv("IQ_ENV_PATH")

        if env_path and Path(env_path).exists():
            load_dotenv(env_path, verbose=False)
            logger.debug(f"Loaded .env from {env_path}")
        elif load_dotenv(verbose=False):
            logger.debug("Loaded .env from current directory")
        # No default load from memory path (not an env file)

        # Resolve project root (repo root)
        project_root: Path = Path(__file__).parents[2].resolve()

        # Transport
        transport_raw = (args.transport or os.getenv("IQ_TRANSPORT", "stdio")).strip().lower()
        if transport_raw not in TRANSPORT_ENUM:
            valid = ", ".join(sorted({"stdio", "sse", "streamable-http", "http"}))
            raise ValueError(f"Invalid transport '{transport_raw}'. Valid options: {valid}")
        transport: Transport = TRANSPORT_ENUM[transport_raw]

        # Port/Host/Path for HTTP
        # Check PORT (Railway/Heroku standard), then IQ_STREAMABLE_HTTP_PORT, then default
        http_port = args.port or int(
            os.getenv("PORT") or os.getenv("IQ_STREAMABLE_HTTP_PORT") or DEFAULT_PORT
        )
        http_host = args.http_host or os.getenv("IQ_STREAMABLE_HTTP_HOST")
        http_path = args.http_path or os.getenv("IQ_STREAMABLE_HTTP_PATH")

        # Memory path precedence: CLI > env > default(project_root/memory.jsonl) > example.jsonl

        memory_path_input = args.memory_path or os.getenv(
            "IQ_MEMORY_PATH", str(DEFAULT_MEMORY_PATH)
        )
        memory_path = Path(str(memory_path_input)).resolve()

        # Disable emojis if desired
        no_emojis = args.no_emojis or os.getenv("IQ_NO_EMOJIS", "false").lower() == "true"

        # Dry Run option - prevents saving to memory file or Supabase
        dry_run = args.dry_run or os.getenv("IQ_DRY_RUN", "false").lower() == "true"
        if dry_run:
            logger.warning(
                "🚧 Dry run mode enabled! No changes will be made to the memory file or Supabase."
            )

        # Stateless HTTP mode - for Cursor compatibility
        stateless_http = os.getenv("FASTMCP_STATELESS_HTTP", "false").lower() == "true"

        return cls(
            debug=debug,
            transport=transport,
            port=http_port,
            streamable_http_host=http_host,
            streamable_http_path=http_path,
            memory_path=memory_path,
            project_root=project_root,
            no_emojis=no_emojis,
            dry_run=dry_run,
            stateless_http=stateless_http,
        )


class SupabaseConfig:
    """Optional Supabase integration configuration.

    This class handles loading Supabase-specific settings from CLI args and env vars.
    Only loaded if Supabase integration is enabled.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        url: str | None,
        key: str | None,
        dry_run: bool,
        email_table: str = "emailSummaries",
        entities_table: str = "kgEntities",
        observations_table: str = "kgObservations",
        relations_table: str = "kgRelations",
        user_info_table: str = "kgUserInfo",
    ) -> None:
        self.enabled = bool(enabled)
        self.url = url or os.getenv("IQ_SUPABASE_URL", None)
        self.key = key or os.getenv("IQ_SUPABASE_KEY", None)
        self.dry_run = dry_run
        self.email_table = email_table
        self.entities_table = entities_table
        self.observations_table = observations_table
        self.relations_table = relations_table
        self.user_info_table = user_info_table

    @classmethod
    def load(cls, dry_run: bool = False) -> "SupabaseConfig" | None:
        """Load Supabase configuration from CLI args and environment variables.

        Args:
            dry_run: Whether to enable dry-run mode

        Returns:
            SupabaseConfig instance (may be enabled or disabled)
        """
        # Parse CLI args for Supabase
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--enable-supabase", action="store_true", default=None)
        parser.add_argument("--supabase-url", type=str, default=None)
        parser.add_argument("--supabase-key", type=str, default=None)
        args, _ = parser.parse_known_args()

        # Check if Supabase is enabled: CLI > env > default (False)
        enabled = (
            args.enable_supabase
            if args.enable_supabase is not None
            else os.getenv("IQ_ENABLE_SUPABASE", "false").lower() == "true"
        )
        if enabled:
            logger.info("Supabase integration is enabled!")
        else:
            logger.info("Supabase integration is disabled!")
            return None

        # Supabase URL: CLI > IQ_SUPABASE_URL env > SUPABASE_URL env (backward compat)
        url = args.supabase_url or os.getenv("IQ_SUPABASE_URL")

        # Supabase Key: CLI > IQ_SUPABASE_KEY env > SUPABASE_KEY env (backward compat)
        key = args.supabase_key or os.getenv("IQ_SUPABASE_KEY")

        # Table names: env vars > defaults
        email_table = os.getenv("IQ_SUPABASE_EMAIL_TABLE", "emailSummaries")
        entities_table = os.getenv("IQ_SUPABASE_ENTITIES_TABLE", "kgEntities")
        observations_table = os.getenv("IQ_SUPABASE_OBSERVATIONS_TABLE", "kgObservations")
        relations_table = os.getenv("IQ_SUPABASE_RELATIONS_TABLE", "kgRelations")
        user_info_table = os.getenv("IQ_SUPABASE_USER_INFO_TABLE", "kgUserInfo")

        return cls(
            enabled=enabled,
            url=url,
            key=key,
            dry_run=dry_run,
            email_table=email_table,
            entities_table=entities_table,
            observations_table=observations_table,
            relations_table=relations_table,
            user_info_table=user_info_table,
        )

    def is_valid(self) -> bool:
        """Check if Supabase config is valid (enabled and has required values)."""
        if not self.enabled:
            return False
        return bool(self.url and self.key)


class AppSettings:
    """Composition of core settings and optional integrations.

    This class combines IQSettings (core) with optional integration configs.
    Integrations are loaded on-demand based on enable flags.

    Attributes:
        core: Core IQ-MCP application settings (always loaded)
        supabase: Supabase integration config (loaded if enabled)
    """

    def __init__(
        self,
        *,
        core: IQSettings,
        supabase: SupabaseConfig | None = None,
    ) -> None:
        self.core = core
        self.supabase = supabase

    @classmethod
    def load(cls) -> "AppSettings":
        """Load all settings: core + optional integrations."""
        # Always load core settings
        core = IQSettings.load()

        # Load Supabase config (checks enable flag internally)
        supabase_config = SupabaseConfig.load(dry_run=core.dry_run)

        if not supabase_config:
            return cls(
                core=core,
                supabase=None,
            )

        # Only include if enabled and valid
        supabase = supabase_config if supabase_config.is_valid() else None
        if supabase:
            logger.debug(f"Supabase config loaded: {supabase}")
        else:
            logger.debug("Supabase config not loaded!")

        return cls(
            core=core,
            supabase=supabase,
        )

    # Convenience properties for backward compatibility
    @property
    def debug(self) -> bool:
        return self.core.debug

    @property
    def transport(self) -> Transport:
        return self.core.transport

    @property
    def port(self) -> int:
        return self.core.port

    @property
    def memory_path(self) -> str:
        return self.core.memory_path

    @property
    def streamable_http_host(self) -> str | None:
        return self.core.streamable_http_host

    @property
    def streamable_http_path(self) -> str | None:
        return self.core.streamable_http_path

    @property
    def project_root(self) -> Path:
        return self.core.project_root

    @property
    def no_emojis(self) -> bool:
        return self.core.no_emojis

    @property
    def dry_run(self) -> bool:
        return self.core.dry_run

    @property
    def supabase_enabled(self) -> bool:
        """Check if Supabase integration is enabled."""
        return self.supabase is not None and self.supabase.enabled

    @property
    def stateless_http(self) -> bool:
        """Check if stateless HTTP mode is enabled (for Cursor compatibility)."""
        return self.core.stateless_http


__all__ = ["AppSettings", "IQSettings", "SupabaseConfig"]
