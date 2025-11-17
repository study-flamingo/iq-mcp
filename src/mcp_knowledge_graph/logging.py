"""Centralized logging for the IQ-MCP server."""

import logging as lg
from pathlib import Path
from .settings import Settings as settings

# def get_logger(self) -> lg.Logger:
#     """Get the main logger for the IQ-MCP server, configured by the settings object."""
#     logger = lg.getLogger("iq-mcp")
#     logger.addHandler(lg.FileHandler(f"{self.project_root}/iq-mcp.log"))
#     logger.setLevel(lg.DEBUG if self.debug else lg.INFO)
#     logger.debug("Retrieved debug logger")
#     return logger


def get_iq_mcp_logger() -> lg.Logger:
    """Get the logger for the IQ-MCP server, configured by the settings object."""
    lg.basicConfig(level=lg.DEBUG if settings.debug else lg.INFO)
    logger = lg.getLogger("iq-mcp")
    root_log_path = settings.project_root / "iq-mcp.log"
    root_log_path = Path(root_log_path).resolve()
    logger.addHandler(
        lg.FileHandler(
            filename=root_log_path,
            encoding="utf-8",
        )
    )
    logger.debug("Retrieved debug logger")
    return logger


logger = get_iq_mcp_logger()

__all__ = ["logger"]
