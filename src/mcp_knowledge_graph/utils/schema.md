# Overview of current knowledge graph data schema

## version tag (alpha)

```json
{
    "type": "version",
    "version": str  // e.g. v1.2.3
}
```

## user_info

```json
{
    "type": "user_info",
    "data": {
        "preferred_name": str,
        "first_name": str,
        "last_name": str,
        "middle_names": list [str],
        "pronouns": str,
        "nickname": str | None,
        "prefixes": list [str],
        "suffixes": list [str],
        "emails": list [str],
        "base_name": str | None,
        "names": list [str]
    }
}
```

## entities

```json
{
    "type": "entity",
    "data": {
        "name": str,
        "entity_type": str,
        "observations": [
            {
                "content": str,
                "durability": str,
                "timestamp": str
            }
        ],
        "aliases":list [str],
        "icon": str  // a single emoji
    }
}
```

## relations

```json
{
    "type": "relation",
    "data": {
        "from_id": str,
        "to_id": str,
        "relation": str
    }
}
```

Data validation at object level is handled by pydantic.

---

## Improvement ideas

  1.
