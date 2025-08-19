"""
Enhanced MCP server for knowledge graph memory.
"""

import logging
import asyncio
from .server import start_server
from .settings import settings

# Default memory path constant
DEFAULT_MEMORY_PATH = "./memory.json"


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("iq-mcp")
    if settings.debug:
        logger.setLevel(logging.DEBUG)

    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("🛑 Received KeyboardInterrupt, shutting down...")
        exit(0)
    except Exception as e:
        logger.error(f"❌ IQ-MCP encountered a critical error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
