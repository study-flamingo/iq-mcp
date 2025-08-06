"""Entry point when running as a module."""

import logging
import os
from dotenv import load_dotenv
from .server import run_sync
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("iq-mcp")

# .env path can be specified with environment variable
IQ_ENV_PATH = os.getenv("IQ_ENV_PATH", ".env")

# .env file support
if not load_dotenv():
    logger.warning("⚠️ No .env file found")

IQ_DEBUG = bool(os.getenv("IQ_DEBUG", "false").lower() == "true")
if IQ_DEBUG:
    logger.setLevel(logging.DEBUG)


def main():
    # Memory path can be specified via environment variable
    try:
        IQ_MEMORY_PATH = Path(os.getenv("IQ_MEMORY_PATH", "../../memory.jsonl")).resolve()
        logger.debug(f"Memory path: {IQ_MEMORY_PATH}")
    except Exception as e:
        raise FileNotFoundError(f"Memory path error: {e}")

    logger.debug("Running IQ-MCP as a module")
    run_sync()

if __name__ == "__main__":
    main()