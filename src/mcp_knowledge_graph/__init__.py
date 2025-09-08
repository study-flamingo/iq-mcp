"""
IQ-MCP Knowledge Graph MCP Server package.

Lightweight package init without importing heavy submodules to avoid side effects
during test discovery and simple metadata imports. Import submodules directly,
e.g. `from mcp_knowledge_graph.manager import KnowledgeGraphManager`.
"""

__version__ = "1.1.0"
__author__ = "study-flamingo"
__email__ = "y9agf5y5@anonaddy.me"

__all__: list[str] = [
    "__version__",
    "__author__",
    "__email__",
]