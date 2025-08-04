"""
Enhanced MCP server for knowledge graph memory with temporal observations.

This package provides a knowledge graph-based memory system for LLMs with
temporal observation support, smart cleanup, and backward compatibility.
"""

__version__ = "0.7.0"
__author__ = "Dr. Joel Casimir"
__email__ = "jc214x@gmail.com"

from .models import (
    TimestampedObservation,
    ObservationInput,
    Entity,
    Relation,
    KnowledgeGraph,
    DurabilityType,
)
from .manager import KnowledgeGraphManager
from .server import mcp

__all__ = [
    "TimestampedObservation",
    "ObservationInput", 
    "Entity",
    "Relation",
    "KnowledgeGraph",
    "DurabilityType",
    "KnowledgeGraphManager",
    "mcp",
]