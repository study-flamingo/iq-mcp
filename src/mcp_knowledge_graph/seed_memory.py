from __future__ import annotations

import argparse
import json
from pathlib import Path
from .models import Entity, Relation

def build_initial_graph() -> list[dict]:
    """Return a minimal initialized knowledge graph using Pydantic models.

    Output mirrors example.jsonl: JSON Lines with entries of type "entity" and "relation".
    Entities and relations are constructed via models to remain consistent with schema changes.
    """
    user_entity = Entity(name="default_user", entity_type="user")
    assistant_entity = Entity(name="default_assistant", entity_type="assistant")

    relation_user_to_assistant = Relation(
        from_entity=user_entity.name,
        to_entity=assistant_entity.name,
        relation_type="has an AI assistant named",
    )
    relation_assistant_to_user = Relation(
        from_entity=assistant_entity.name,
        to_entity=user_entity.name,
        relation_type="is the AI assistant of",
    )

    def to_entity_record(entity: Entity) -> dict:
        return {"type": "entity", "data": entity.model_dump(exclude_none=True)}

    def to_relation_record(relation: Relation) -> dict:
        data = relation.model_dump(exclude_none=True)
        # Map model field names to external JSONL schema keys for compatibility with example.jsonl
        if "from_entity" in data:
            data["from"] = data.pop("from_entity")
        if "to_entity" in data:
            data["to"] = data.pop("to_entity")
        return {"type": "relation", "data": data}

    records: list[dict] = [
        to_entity_record(user_entity),
        to_entity_record(assistant_entity),
        to_relation_record(relation_user_to_assistant),
        to_relation_record(relation_assistant_to_user),
    ]

    return records


def write_jsonl(output_path: Path, records: list[dict], overwrite: bool = False) -> None:
    """Write records to a JSONL file at output_path, creating parent dirs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        if overwrite:
            print(f"WARNING: Overwriting {output_path} with new initial graph")
        else:
            raise FileExistsError(f"Error: {output_path} already exists! Choose a different path, or use --overwrite to overwrite (DESTRUCTIVE)")
        for r in records:
            r.write(json.dumps(r, ensure_ascii=False))
            r.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=
        "Write a freshly-initialized knowledge graph (JSONL) to the given path."
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

    records = build_initial_graph()
    write_jsonl(args.output, records)


if __name__ == "__main__":
    main()

__all__ = ["main", "build_initial_graph"]