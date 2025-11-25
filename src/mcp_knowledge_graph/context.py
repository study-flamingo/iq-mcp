"""
Application context for runtime state.

This module provides a centralized container for runtime dependencies
(settings, logger, supabase manager) that are initialized once at startup
and accessed throughout the application.

Usage:
    from .context import ctx

    # At startup (in __main__.py or server.py):
    ctx.init()

    # Anywhere else:
    ctx.settings.debug
    ctx.logger.info("...")
    if ctx.supabase:
        await ctx.supabase.get_email_summaries()
"""

from __future__ import annotations

import logging as lg
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .settings import AppSettings
    from .supabase_manager import SupabaseManager


class AppContext:
    """
    Singleton container for application runtime state.

    Attributes:
        settings: Application settings (loaded from CLI/env/defaults)
        logger: Configured logger instance
        supabase: Optional Supabase manager (None if disabled)
    """

    _instance: "AppContext | None" = None
    _initialized: bool = False

    def __new__(cls) -> "AppContext":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Avoid re-initializing on repeated __init__ calls
        pass

    def init(self) -> "AppContext":
        """
        Initialize the application context. Call once at startup.

        Loads settings, configures logging, and optionally initializes
        the Supabase manager based on configuration.

        Returns:
            self for method chaining
        """
        if self._initialized:
            return self

        # Import here to avoid circular imports and control load order
        from .settings import AppSettings
        from .supabase_manager import SupabaseManager

        # Load settings
        self._settings = AppSettings.load()

        # Configure logger
        self._logger = self._configure_logger()

        # Initialize Supabase manager if enabled
        if self._settings.supabase_enabled and self._settings.supabase:
            self._supabase: SupabaseManager | None = SupabaseManager(self._settings.supabase)
            self._logger.debug("Supabase manager initialized")
        else:
            self._supabase = None
            self._logger.debug("Supabase integration disabled")

        self._initialized = True
        return self

    def _configure_logger(self) -> lg.Logger:
        """Configure and return the application logger."""
        lg.basicConfig(level=lg.DEBUG if self._settings.debug else lg.INFO)
        logger = lg.getLogger("iq-mcp")

        # Add file handler
        log_path = Path(self._settings.project_root) / "iq-mcp.log"
        file_handler = lg.FileHandler(filename=log_path, encoding="utf-8")
        file_handler.setLevel(lg.DEBUG if self._settings.debug else lg.INFO)
        logger.addHandler(file_handler)

        return logger

    @property
    def settings(self) -> "AppSettings":
        """Get application settings. Raises if not initialized."""
        if not self._initialized:
            raise RuntimeError("AppContext not initialized. Call ctx.init() first.")
        return self._settings

    @property
    def logger(self) -> lg.Logger:
        """Get configured logger. Raises if not initialized."""
        if not self._initialized:
            raise RuntimeError("AppContext not initialized. Call ctx.init() first.")
        return self._logger

    @property
    def supabase(self) -> "SupabaseManager | None":
        """Get Supabase manager (None if disabled). Raises if not initialized."""
        if not self._initialized:
            raise RuntimeError("AppContext not initialized. Call ctx.init() first.")
        return self._supabase

    @property
    def is_initialized(self) -> bool:
        """Check if context has been initialized."""
        return self._initialized


# Global context instance - import this
ctx = AppContext()

__all__ = ["ctx", "AppContext"]
