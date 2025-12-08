"""
Centralized logging for the IQ-MCP server.

This module provides a lazy logger accessor that uses the application context.
The logger is configured when the context is initialized at startup.

Usage:
    from .iq_logging import logger
    logger.info("message")  # Works after ctx.init() is called
"""

from __future__ import annotations

import logging as lg
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class _LazyLogger:
    """
    Lazy proxy for the application logger.
    
    Defers to ctx.logger after initialization, providing a fallback
    bootstrap logger before ctx.init() is called.
    """
    
    _bootstrap_logger: lg.Logger | None = None
    
    def _get_logger(self) -> lg.Logger:
        """Get the appropriate logger based on context state."""
        # Import here to avoid circular imports
        from .context import ctx
        
        if ctx.is_initialized:
            return ctx.logger
        
        # Fallback bootstrap logger for early startup messages
        if self._bootstrap_logger is None:
            self._bootstrap_logger = lg.getLogger("iq-mcp-bootstrap")
            self._bootstrap_logger.setLevel(lg.DEBUG)
            if not self._bootstrap_logger.handlers:
                handler = lg.StreamHandler()
                handler.setLevel(lg.DEBUG)
                self._bootstrap_logger.addHandler(handler)
        return self._bootstrap_logger
    
    def __getattr__(self, name: str):
        """Proxy attribute access to the underlying logger."""
        return getattr(self._get_logger(), name)


# Global lazy logger instance
logger = _LazyLogger()

__all__ = ["logger"]
