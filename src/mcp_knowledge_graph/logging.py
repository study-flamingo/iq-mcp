"""Centralized logging for the IQ-MCP server."""

import logging as lg
from .settings import Settings as settings


def get_iq_mcp_logger() -> lg.Logger:
    """Get the logger for the IQ-MCP server, configured by the settings object."""
    lg.basicConfig(level=lg.DEBUG if settings.debug else lg.INFO)
    logger = lg.getLogger("iq-mcp")
    logger.debug("Retrieved debug logger")
    return logger


__all__ = ["get_iq_mcp_logger"]
