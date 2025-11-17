<!-- markdownlint-disable -->
## Workflows — Tools, Manager Methods, and Models

### Read Graph
- Tool: `server.read_graph`
- Manager: `manager.read_graph`
- Models: `KnowledgeGraph`
- Notes: Prints user info (optional), entities, and relations; uses async formatting helpers.

### Read User Info
- Tool: `server.read_user_info`
- Manager: `manager.read_graph`
- Models: `UserIdentifier`
- Notes: Uses `@computed_field` names; linked entity is resolved by `linked_entity_id`.

### Create Entities
- Tool: `server.create_entities`
- Manager: `manager.create_entities`
- Models: `CreateEntityRequest`, `CreateEntityResult`, `Entity`, `Observation`
- Validation: name/type stripped non-empty; `EntityID` generated; emoji validated.

### Create Relations
- Tool: `server.create_relations`
- Manager: `manager.create_relations`
- Models: `CreateRelationRequest`, `CreateRelationResult`, `Relation`
- Validation: endpoints resolved by ID or name; relations use IDs only; no automatic dedupe on save (relations are deduped during `manager.merge_entities` rewrites and during Supabase sync).

### Add Observations
- Tool: `server.add_observations`
- Manager: `manager.apply_observations`
- Models: `ObservationRequest`, `Observation`, `AddObservationResult`
- Validation: content dedup per entity; timestamp via `default_factory`.

### Cleanup Outdated Observations
- Tool: not exposed (manager-only)
- Manager: `manager.cleanup_outdated_observations`
- Models: `CleanupResult`
- Logic: age thresholds by durability; saves only if removals occurred.

### Get Observations by Durability
- Tool: not exposed (manager-only)
- Manager: `manager.get_observations_by_durability`
- Models: `DurabilityGroupedObservations`

### Open Nodes
- Tool: `server.open_nodes`
- Manager: `manager.open_nodes`
- Models: `Entity` (manager); Tool returns formatted text
- Notes: Filters target entities + relations among them.

### Search Nodes
- Tool: `server.search_nodes`
- Manager: `manager.search_nodes`
- Models: `KnowledgeGraph`
- Logic: search name/type/aliases/observation content; filters relations for matched entities.

### Merge Entities
- Tool: `server.merge_entities`
- Manager: `manager.merge_entities`
- Models: `Entity`, `Relation`
- Validation: new name conflict checks; merged aliases; relations rewritten and deduped.

### Update Entity
- Tool: `server.update_entity`
- Manager: `manager.update_entity`
- Models: `UpdateEntityRequest`, `UpdateEntityResult`, `Entity`
- Validation: prevents name/alias conflicts; supports merging or replacing aliases; emoji validation applies.

### Update User Info
- Tool: `server.update_user_info`
- Manager: `manager.update_user_info(UserIdentifier)`
- Models: `UserIdentifier`
- Validation: `linked_entity_id` must exist; names derived; IDs validated.

### Supabase Integration (optional)
- Tools (added only if Supabase is initialized):
  - `server.get_new_email_summaries` → `SupabaseManager.get_email_summaries`
  - `server.sync_supabase` → `manager.sync_supabase`
- Tables used (defaults): `emailSummaries`, `kgEntities`, `kgObservations`, `kgRelations`. See `docs/SUPABASE_SCHEMA.md`.

### Delete Entry (Unified) — Deprecated
- Tool: `server.delete_entry`
- Manager: `manager.delete_entities|delete_observations|delete_relations`
- Models: `DeleteEntryRequest`
- Caution: destructive; ensure explicit confirmation.

### Storage & Meta
- Loader: `manager._load_graph()` uses `MemoryRecord.model_validate_json()`
- Saver: `manager._save_graph()` writes `meta` (GraphMeta), then `user_info`, then entities and relations.
- Versioning: use `GraphMeta.schema_version` and migration hooks when altering storage.
