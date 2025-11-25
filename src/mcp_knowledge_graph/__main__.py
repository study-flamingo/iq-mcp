"""
Enhanced MCP server for knowledge graph memory.
"""

import asyncio
from .settings import settings
from .iq_logging import logger
from .server import start_server


def main():
    try:
        logger.info(f"🔍 Memory path: {settings.memory_path}")
        logger.debug("🚀 Starting IQ-MCP server...")
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("👋 Received KeyboardInterrupt, shutting down gracefully...")
        exit(0)
    except Exception as e:
        error = f"⛔ IQ-MCP encountered an uncaught exception: {e}"
        logger.error(error)
        raise RuntimeError(error)
        # exit(1)


if __name__ == "__main__":
    main()
