from __future__ import annotations

import argparse
import json
from pathlib import Path
from .models import Entity, KnowledgeGraph, Relation, UserIdentifier

def build_initial_graph(user_info: UserIdentifier| None = None) -> KnowledgeGraph:
    """Return a minimal initialized knowledge graph using Pydantic models.

    Output mirrors example.jsonl: JSON Lines with entries of type "entity" and "relation".
    Entities and relations are constructed via models to remain consistent with schema changes.
    """
    if user_info is None:
        user_info = UserIdentifier.from_default()
    else:
        user_info = user_info
    
    user_entity = Entity(name=user_info.names[0], entity_type="user")
    assistant_entity = Entity(name="assistant", entity_type="AI assistant")

    # Create seed entries for the new graph
    relation_user_to_assistant = Relation.from_entities(
        from_entity=user_entity,
        to_entity=assistant_entity,
        relation="has an AI assistant named",
    )
    relation_assistant_to_user = Relation.from_entities(
        from_entity=assistant_entity,
        to_entity=user_entity,
        relation="is the AI assistant of",
    )

    graph = KnowledgeGraph.from_components(
        user_info=user_info,
        entities=[user_entity, assistant_entity],
        relations=[relation_user_to_assistant, relation_assistant_to_user],
    )
    return graph

def write_jsonl(output_path: Path | None, records: list[dict], overwrite: bool = False) -> None:
    """Write records to a JSONL file at output_path, creating parent dirs."""
    if output_path is None:
        print("⚠️ WARNING: No output path provided, using current directory")
        output_path = Path.cwd() / "memory.jsonl"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        if overwrite:
            print(f"⚠️ WARNING: Overwriting {output_path} with new initial graph")
        else:
            raise FileExistsError(f"Error: {output_path} already exists! Choose a different path, or use --overwrite to overwrite (DESTRUCTIVE)")
        for r in records:
            r.write(json.dumps(r, ensure_ascii=False))
            r.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        name="IQ-MCP: iq-mcp-init / seed_memory utility tool",
        description="Write a freshly-initialized knowledge graph (JSONL) to the given path, or current directory if no path is provided."
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Path to write the JSONL knowledge graph (e.g., memory_dev.jsonl)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing file at output path instead of raising an error. **CAUTION** This will IRREVERSIBLY delete all existing data in the destination file!",
    )
    args = parser.parse_args()

    new_graph = build_initial_graph()
    write_jsonl(args.output, new_graph.to_dict())


if __name__ == "__main__":
    main()

__all__ = ["main", "build_initial_graph"]