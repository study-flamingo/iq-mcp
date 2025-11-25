import asyncio
import logging
import argparse

from mcp_knowledge_graph.models import KnowledgeGraph
from mcp_knowledge_graph.settings import settings
from mcp_knowledge_graph.manager import KnowledgeGraphManager
from mcp_knowledge_graph.supabase_manager import SupabaseManager

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("supabase_utils.py")


async def main():
    logger.info("IQ-MCP Supabase Utils")
    logger.info(
        "Currently, this script serves to recreate the knowledge graph in Supabase from a local JSONL file."
    )
    logger.info(
        "By default, the script will run in dry-run mode, and will not actually perform the operation."
    )
    logger.info("Run with --execute to actually perform the operation.")

    parser = argparse.ArgumentParser(description="IQ-MCP Supabase Utils")
    parser.add_argument("--execute", action="store_true", help="Actually perform the operation.")
    args = parser.parse_args()

    if args.execute:
        logger.info("Executing operation...")
    else:
        logger.info("Dry-run mode, no operation will be performed.")

    manager = KnowledgeGraphManager(settings.memory_path)
    logger.info(
        f"Local manager initialized, loading graph from local JSONL file at '{settings.memory_path}'..."
    )
    graph: KnowledgeGraph = await manager._load_graph(force_local=True)

    try:
        graph.validate()
    except Exception as e:
        logger.error(f"Error validating graph after loading from local JSONL file: {e}")
        logger.error(
            f"There may be an issue with the local JSONL file. Please check the file and try again."
        )
        exit(1)
    logger.info("Graph validated successfully.")

    if args.execute:
        logger.info("Initializing Supabase manager and client...")
        supabase_manager = SupabaseManager(settings.supabase)
        logger.info("Saving graph to Supabase...")
        try:
            await supabase_manager.save_knowledge_graph(graph)
        except Exception as e:
            logger.error(f"Error saving graph to Supabase: {e}")
            logger.error(
                f"There may be an issue with the Supabase connection. Please check the connection and try again."
            )
            exit(1)
        logger.info("Graph saved to Supabase successfully!")
    else:
        logger.info(
            "🏅 Graph successfully loaded and validated, should be ready to execute. (Currently in dry-run mode, no operation performed.)"
        )


if __name__ == "__main__":
    asyncio.run(main())
    exit(0)
