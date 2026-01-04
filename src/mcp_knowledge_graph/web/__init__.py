"""
Web UI module for interactive graph visualization.

This module provides a web-based interface for viewing and editing
the knowledge graph, accessible at /graph when HTTP transport is enabled.
"""

from .routes import create_web_app

__all__ = ["create_web_app"]
