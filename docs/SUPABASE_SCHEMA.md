The SupaBase database for cloud memory storage should be constructed as follows:

```sql
-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.emailSummaries (
  index bigint GENERATED ALWAYS AS IDENTITY NOT NULL UNIQUE,
  received_at timestamp without time zone,
  processed_at timestamp without time zone NOT NULL DEFAULT now(),
  labels ARRAY,
  message_id text NOT NULL UNIQUE,
  thread_id text,
  to text,
  from_address text,
  from_name text,
  reply_to text,
  subject text,
  text_summary text,
  links ARRAY,
  reviewed boolean NOT NULL DEFAULT false,
  CONSTRAINT emailSummaries_pkey PRIMARY KEY (index)
);
CREATE TABLE public.kgEntities (
  key bigint GENERATED ALWAYS AS IDENTITY NOT NULL UNIQUE,
  id text NOT NULL DEFAULT ''::text UNIQUE,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  entity_name text DEFAULT ''::text,
  aliases ARRAY NOT NULL,
  is_user boolean NOT NULL DEFAULT false,
  CONSTRAINT kgEntities_pkey PRIMARY KEY (key)
);
CREATE TABLE public.kgObservations (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  content text DEFAULT ''::text,
  linked_entity text NOT NULL DEFAULT ''::text,
  durability USER-DEFINED NOT NULL DEFAULT 'short-term'::"DURABILITY",
  CONSTRAINT kgObservations_pkey PRIMARY KEY (id, linked_entity),
  CONSTRAINT kgObservations_linked_entity_fkey FOREIGN KEY (linked_entity) REFERENCES public.kgEntities(id)
);
CREATE TABLE public.kgRelations (
  from text NOT NULL,
  to text NOT NULL,
  content text NOT NULL DEFAULT ''::text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT kgRelations_pkey PRIMARY KEY (from),
  CONSTRAINT kgRelations_from_fkey FOREIGN KEY (from) REFERENCES public.kgEntities(id)
);
```
