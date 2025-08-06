"""Entry point when running as a module."""

import logging
import os
import asyncio
from dotenv import load_dotenv
from .server import start_server
from pathlib import Path

# Default memory path constant
DEFAULT_MEMORY_PATH = "./memory.json"


def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("iq-mcp")

    if load_dotenv(verbose=True):
        logger.info("🌎 .env file loaded")

    # .env path can be specified with environment variable
    IQ_ENV_PATH = os.getenv("IQ_ENV_PATH", ".env")

    if Path(IQ_ENV_PATH).is_file():
        if load_dotenv(IQ_ENV_PATH):
            logger.info(f"🌎 .env file loaded from {IQ_ENV_PATH}")
        else:
            logger.error("⛔ Bad .env file, unable to load")

    IQ_DEBUG = bool(os.getenv("IQ_DEBUG", "false").lower() == "true")
    if IQ_DEBUG:
        logger.info("🐞 IQ-MCP is running in debug mode")
        logger.setLevel(logging.DEBUG)

    # Memory path can be specified via environment variable
    try:
        IQ_MEMORY_PATH = Path(os.getenv("IQ_MEMORY_PATH", DEFAULT_MEMORY_PATH)).resolve()
        logger.debug(f"Memory path: {IQ_MEMORY_PATH}")
    except Exception as e:
        raise FileNotFoundError(f"Memory file path error: {e}")

    logger.debug("Running IQ-MCP as a module")
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
