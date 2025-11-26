"""Migrate a graph from a previous version to a new version.
See schema.md for more information on the current data architecture."""

import json
import argparse
from typing import Any

from mcp_knowledge_graph.manager import generate_entity_id
from mcp_knowledge_graph.models import (
    UserIdentifier,
    Entity,
    Relation,
    KnowledgeGraph,
)

CURRENT_VERSION = "1.3.0"
DRY_RUN = False
IGNORE_ERRORS = False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        name="IQ-MCP: iq-mcp graph migration utility tool",
        description="Migrate a graph from a previous version to a new version.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not actually write to the output file, and instead print results to the console.",
    )
    parser.add_argument(
        "--path",
        type=str,
        required=True,
        help="Absolute path to the knowledge graph JSONL file.",
    )
    parser.add_argument(
        "--ignore-errors",
        type=str,
        required=False,
        help="Ignore errors and continue processing the file. Invalid objects will be skipped. This means that invalid objects WILL BE REMOVED FROM THE GRAPH! *Strongly* recommend using --dry-run first.",
    )
    parser.add_argument(
        "--no-backup",
        type=str,
        required=False,
        help="By default, the old graph will be renamed and kept as a backup in case reversal is desired. Setting this argument will skip the backup, and update the file in place.",
    )
    return parser.parse_args()


def migrate_graph(path: str, dry_run: bool = False) -> KnowledgeGraph:
    """Migrate a graph from a previous version to the current version."""

    old_version = None
    with open(path, "r", encoding="utf-8") as f:
        lines_raw: list[str] = []
        try:
            for line in f:
                lines_raw.append(f.readline(size=1))
        except json.JSONDecodeError as e:
            raise SystemExit(f"Invalid JSON line: {e}\nLine: {line}")
        except Exception as e:
            raise SystemExit(f"Error reading file: {e}")

        i = -1
        new_user_info: UserIdentifier | None = None
        for line in lines_raw:
            i += 1  # increment at start to avoid interruption by errors
            try:
                line = line.strip()
                if not line:
                    if i == 0:  # if first line is empty, assume empty file
                        raise SystemExit("Empty file")
                    continue  # handle newlines
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as e:
                    if IGNORE_ERRORS:
                        continue
                    raise SystemExit(f"Invalid JSON line: {e}\nLine: {line[:200]}")

                # Version object should be first, unless it's a really old version
                if i == 0:
                    if obj.get("type") == "version":
                        old_version = obj.get("version") or None
                    if not old_version:
                        print("Missing or invalid version object, this must be an old one...")

                typ = obj.get("type")
                data = obj.get("data", {})

                # Here's where the magic happens
                match typ:
                    case "user_info":
                        raw_user_info: dict[str, Any] = {}
                        raw_user_info["preferred_name"] = (
                            data.get("preferred_name") if data.get("preferred_name") else None
                        )
                        raw_user_info["first_name"] = (
                            data.get("first_name") if data.get("first_name") else None
                        )
                        raw_user_info["last_name"] = (
                            data.get("last_name") if data.get("last_name") else None
                        )
                        raw_user_info["middle_names"] = (
                            data.get("middle_names") if data.get("middle_names") else []
                        )
                        raw_user_info["pronouns"] = (
                            data.get("pronouns") if data.get("pronouns") else None
                        )
                        raw_user_info["nickname"] = (
                            data.get("nickname") if data.get("nickname") else None
                        )
                        new_user_info = UserIdentifier.from_dict(raw_user_info)

                    case "entity":
                        raw_entity: dict[str, Any] = {}
                        raw_entity["id"]: str = data.get("id") if data.get("id") else None
                        raw_entity["name"]: str = data.get("name") if data.get("name") else None
                        raw_entity["observations"]: list[Any] = (
                            data.get("observations") if data.get("observations") else []
                        )
                        raw_entity["aliases"]: list[str] = (
                            data.get("aliases") if data.get("aliases") else []
                        )
                        raw_entity["icon"]: str = data.get("icon") if data.get("icon") else None
                        raw_entity["entity_type"]: str = (
                            data.get("entity_type") if data.get("entity_type") else None
                        )

                        if not raw_entity["id"]:
                            raw_entity["id"]: str = generate_entity_id()
                        if not raw_entity["name"]:
                            raise ValueError("Entity at line {i} has no name")
                        if not raw_entity["entity_type"]:
                            raise ValueError("Entity at line {i} has no entity type")

                        new_entity = Entity.from_dict(raw_entity)
                    case "relation":
                        raw_relation: dict[str, Any] = {}
                        raw_relation["from_id"] = (
                            data.get("from_id") if data.get("from_id") else None
                        )
                        raw_relation["to_id"] = data.get("to_id") if data.get("to_id") else None
                        raw_relation["relation"] = (
                            data.get("relation") if data.get("relation") else None
                        )
                        new_relation = Relation(**raw_relation)
                    case _:
                        raise ValueError(f"Invalid type: {typ}")

                if not dry_run:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(json.dumps(obj) + "\n")
                if typ == "user_info":
                    print(f"Updated line {i}: User info: {new_user_info}")
                if typ == "entity":
                    print(f"Updated line {i}: Entity: {new_entity}")
                if typ == "relation":
                    print(f"Updated line {i}: Relation: {new_relation}")

            except Exception as e:
                if IGNORE_ERRORS:
                    print(f"Bad line: {e}")
                else:
                    raise RuntimeError(f"Error migrating graph: {e}")

    return None


def main():
    """Main function."""
    pass


if __name__ == "__main__":
    main()
