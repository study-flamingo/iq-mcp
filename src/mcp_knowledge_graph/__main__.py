"""
Enhanced MCP server for knowledge graph memory.
"""

import argparse
import asyncio
import sys
from .context import ctx
from .iq_logging import logger
from .server import start_server
from .version import IQ_MCP_VERSION


def main():
    # Parse version flag early, before any initialization
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-v", "--version", action="store_true")
    args, _ = parser.parse_known_args()

    if args.version:
        print(IQ_MCP_VERSION)
        sys.exit(0)

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
