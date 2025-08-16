"""
Enhanced MCP server for knowledge graph memory.
"""

__version__ = "0.1.0"
__author__ = "study-flamingo"
__email__ = "y9agf5y5@anonaddy.me"

from .models import (
    Observation,
    Entity,
    Relation,
    KnowledgeGraph,
    DurabilityType,
)
from .manager import KnowledgeGraphManager
from .server import mcp

__all__ = [
    "Observation",
    "Entity",
    "Relation",
    "KnowledgeGraph",
    "DurabilityType",
    "KnowledgeGraphManager",
    "mcp",
]