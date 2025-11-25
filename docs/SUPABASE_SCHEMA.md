# Supabase Schema

**Schema Version:** 1

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
  created_at timestamp with time zone
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

1. **Delete** existing data (relations → observations → entities → user_info)
2. **Insert** fresh data (entities → observations → relations → user_info)

This is a full replacement, not incremental sync.

## Versioning

- Code expects Supabase schema version 1 (see `SUPABASE_SCHEMA_VERSION` in `supabase_manager.py`)
- When changing table/column contracts incompatibly:
  1. Bump `SUPABASE_SCHEMA_VERSION`
  2. Update this document with `[version: N]`
  3. Provide a migration note
