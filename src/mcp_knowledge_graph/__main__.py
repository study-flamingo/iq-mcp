"""
Enhanced MCP server for knowledge graph memory.
"""

import asyncio
from .context import ctx
from .iq_logging import logger
from .server import start_server


def main():
    try:
        # Initialize context first to get settings and logger
        ctx.init()
        logger.info(f"🔍 Memory path: {ctx.settings.memory_path}")
        logger.debug("🚀 Starting IQ-MCP server...")
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("👋 Received KeyboardInterrupt, shutting down gracefully...")
        exit(0)
    except Exception as e:
        error = f"⛔ IQ-MCP encountered an uncaught exception: {e}"
        logger.error(error)
        raise RuntimeError(error)


if __name__ == "__main__":
    main()
