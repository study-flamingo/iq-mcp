The SupaBase database for cloud memory storage should be constructed as follows:

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

-- Entities table used by Supabase sync
CREATE TABLE public.kgEntities (
  id text PRIMARY KEY,
  name text NOT NULL,
  entity_type text NOT NULL,
  aliases text[] NOT NULL DEFAULT '{}',
  icon text,
  ctime timestamp with time zone,
  mtime timestamp with time zone
);

-- Observations table used by Supabase sync
CREATE TABLE public.kgObservations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  linked_entity text NOT NULL REFERENCES public.kgEntities(id) ON DELETE CASCADE,
  content text NOT NULL,
  durability text NOT NULL,
  timestamp timestamp with time zone
);

-- Relations table used by Supabase sync
CREATE TABLE public.kgRelations (
  from_id text NOT NULL REFERENCES public.kgEntities(id) ON DELETE CASCADE,
  to_id text NOT NULL REFERENCES public.kgEntities(id) ON DELETE CASCADE,
  relation text NOT NULL,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  PRIMARY KEY (from_id, to_id, relation)
);
```
