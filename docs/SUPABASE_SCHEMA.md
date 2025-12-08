# Supabase Schema

**Schema Version:** 2

The Supabase database for cloud memory storage should be constructed as follows:

```sql
-- WARNING: This schema is for context only and is not meant to be run.
-- It reflects the columns used by the current Supabase integration in code.

-- Email summaries (used by get_new_email_summaries)
CREATE TABLE public.emailSummaries (
  index bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  received_at timestamp with time zone,
  processed_at timestamp with time zone NOT NULL DEFAULT now(),
  labels jsonb,
  message_id text NOT NULL UNIQUE,
  thread_id text,
  to text,
  from_address text,
  from_name text,
  reply_to text,
  subject text,
  text_summary text,
  links jsonb,
  reviewed boolean NOT NULL DEFAULT false
);

-- Entities table
CREATE TABLE public.kgEntities (
  id text PRIMARY KEY,
  name text NOT NULL,
  type text NOT NULL,
  aliases text[] NOT NULL DEFAULT '{}',
  icon text,
  created_at timestamp with time zone,
  modified_at timestamp with time zone
);

-- Observations table
CREATE TABLE public.kgObservations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  linked_entity text NOT NULL REFERENCES public.kgEntities(id) ON DELETE CASCADE,
  content text NOT NULL,
  durability text NOT NULL,
  created_at timestamp with time zone,
  -- Required for upsert support
  UNIQUE (linked_entity, content)
);

-- Relations table
CREATE TABLE public.kgRelations (
  "from" text NOT NULL REFERENCES public.kgEntities(id) ON DELETE CASCADE,
  "to" text NOT NULL REFERENCES public.kgEntities(id) ON DELETE CASCADE,
  content text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY ("from", "to", content)
);

-- User info table
CREATE TABLE public.kgUserInfo (
  linked_entity_id text PRIMARY KEY REFERENCES public.kgEntities(id),
  preferred_name text,
  first_name text,
  last_name text,
  middle_names text[],
  pronouns text,
  nickname text,
  prefixes text[],
  suffixes text[],
  emails text[],
  base_name text[],
  names text[]
);
```

## Table Mapping

| Local Model | Supabase Table | Notes |
|-------------|----------------|-------|
| `Entity` | `kgEntities` | Core entity data |
| `Observation` | `kgObservations` | Linked to entities via `linked_entity` FK |
| `Relation` | `kgRelations` | Uses `from`/`to` columns (quoted due to reserved word) |
| `UserIdentifier` | `kgUserInfo` | Single row per graph |
| `EmailSummary` | `emailSummaries` | External data source |

## Configuration

Table names can be customized via environment variables:

| Variable | Default |
|----------|---------|
| `IQ_SUPABASE_EMAIL_TABLE` | `emailSummaries` |
| `IQ_SUPABASE_ENTITIES_TABLE` | `kgEntities` |
| `IQ_SUPABASE_OBSERVATIONS_TABLE` | `kgObservations` |
| `IQ_SUPABASE_RELATIONS_TABLE` | `kgRelations` |
| `IQ_SUPABASE_USER_INFO_TABLE` | `kgUserInfo` |

## Sync Behavior

When saving to Supabase (`ctx.supabase.save_knowledge_graph()`):

1. **Upsert** current graph data (entities → observations → relations → user_info)
   - Uses `on_conflict` to safely update existing records or insert new ones
   - Existing data is preserved if upsert fails (no data loss risk)
2. **Clean up** orphaned records (relations → observations → entities)
   - Only removes records for entities that no longer exist in the graph
   - Cleanup failures are logged but don't fail the sync

### Required Unique Constraints

For upserts to work correctly, ensure these constraints exist:

| Table | Constraint Columns |
|-------|-------------------|
| `kgEntities` | `id` (primary key) |
| `kgObservations` | `(linked_entity, content)` |
| `kgRelations` | `(from, to, content)` (primary key) |
| `kgUserInfo` | `linked_entity_id` (primary key) |

## Versioning

- Code expects Supabase schema version 2 (see `SUPABASE_SCHEMA_VERSION` in `supabase_manager.py`)
- When changing table/column contracts incompatibly:
  1. Bump `SUPABASE_SCHEMA_VERSION`
  2. Update this document with `[version: N]`
  3. Provide a migration note

### Migration: v1 → v2

Version 2 changes from delete-then-insert to upserts for safer data handling.

**Required change:** Add unique constraint on `kgObservations`:

```sql
ALTER TABLE public.kgObservations
ADD CONSTRAINT kgObservations_linked_entity_content_key
UNIQUE (linked_entity, content);
```

Note: If you have duplicate (linked_entity, content) pairs, you'll need to dedupe them first:

```sql
-- Find duplicates
SELECT linked_entity, content, COUNT(*)
FROM public.kgObservations
GROUP BY linked_entity, content
HAVING COUNT(*) > 1;

-- Remove duplicates (keeps oldest by created_at)
DELETE FROM public.kgObservations a
USING public.kgObservations b
WHERE a.linked_entity = b.linked_entity
  AND a.content = b.content
  AND a.created_at > b.created_at;
```
