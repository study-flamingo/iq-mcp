"""Entry point when running as a script."""

import logging
import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from src.mcp_knowledge_graph.server import start_server


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("iq-mcp")

    # .env path can be specified with environment variable
    IQ_ENV_PATH = os.getenv("IQ_ENV_PATH", ".env")

    # .env file support
    if not load_dotenv(IQ_ENV_PATH):
        logger.warning("⚠️ No .env file found")
    else:
        logger.info(f"🌎 .env file loaded from {IQ_ENV_PATH}")

    IQ_DEBUG = bool(os.getenv("IQ_DEBUG", "false").lower() == "true")
    if IQ_DEBUG:
        logger.info("🐞 IQ-MCP is running in debug mode")
        logger.setLevel(logging.DEBUG)

    # Memory path can be specified via environment variable
    try:
        IQ_MEMORY_PATH = Path(os.getenv("IQ_MEMORY_PATH", "./memory.jsonl")).resolve()
        logger.debug(f"Memory path: {IQ_MEMORY_PATH}")
    except Exception as e:
        raise FileNotFoundError(f"Memory file path error: {e}")

    logger.debug("Running IQ-MCP as a script")
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        logger.info("🛑 Received KeyboardInterrupt, closing...")
        exit(0)
    except Exception as e:
        logger.error(f"❌ IQ-MCP encountered a critical error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
