"""
Enhanced MCP server for knowledge graph memory.
"""

import asyncio
from .settings import Settings as settings, Logger as logger
from .server import start_server


def main():
    try:
        logger.info(f"🔍 Memory path: {settings.memory_path}")
        logger.debug("🚀 Starting IQ-MCP server...")
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("🛑 Received KeyboardInterrupt, shutting down...")
        exit(0)
    except Exception as e:
        logger.error(f"❌ IQ-MCP encountered a critical error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
