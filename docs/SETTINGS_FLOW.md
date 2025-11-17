# Settings and Initialization Flow

This document explains how the settings and initialization flow works after the composition pattern refactor.

## Architecture Overview

The settings system uses a **composition pattern** to separate core settings from optional integrations:

1. **`IQSettings`**: Core application settings (always loaded)
2. **`SupabaseConfig`**: Optional Supabase integration settings (loaded if enabled)
3. **`Settings`**: Composition class that combines core + optional integrations

## Settings Loading Flow

### Step 1: Module Import
```python
# When settings.py is imported
Settings = Settings.load()  # Executed at module level
```

### Step 2: Settings.load() - Composition
```python
Settings.load()
├── IQSettings.load()        # Always loads core settings
│   ├── Parse CLI args
│   ├── Load env vars (.env)
│   └── Apply defaults
│
└── SupabaseConfig.load()     # Conditionally loads Supabase settings
    ├── Parse CLI args (same parser, different args)
    ├── Check enable flag
    ├── Load URL/key from env vars
    └── Return config (enabled or disabled)
```

### Step 3: Validation and Composition
```python
supabase_config = SupabaseConfig.load(...)
supabase = supabase_config if supabase_config.is_valid() else None

# Return Settings with:
# - core: IQSettings (always present)
# - supabase: SupabaseConfig | None (only if enabled AND valid)
```

## Settings Structure

```python
Settings
├── core: IQSettings
│   ├── debug: bool
│   ├── transport: Transport
│   ├── port: int
│   ├── memory_path: str
│   ├── streamable_http_host: str | None
│   ├── streamable_http_path: str | None
│   ├── project_root: Path
│   ├── no_emojis: bool
│   └── dry_run: bool
│
└── supabase: SupabaseConfig | None
    ├── enabled: bool
    ├── url: str | None
    ├── key: str | None
    └── dry_run: bool
```

## Backward Compatibility

The `Settings` class provides convenience properties that delegate to `core`:

```python
settings.debug          # → settings.core.debug
settings.transport      # → settings.core.transport
settings.memory_path    # → settings.core.memory_path
# ... etc
```

This means existing code like `settings.debug` still works without changes.

## Initialization Flow

### Server Startup (`start_server()`)

```python
async def start_server():
    # 1. Startup checks (memory file validation)
    await startup_check()
    
    # 2. Configure transport
    validated_transport = settings.transport
    # ... transport kwargs
    
    # 3. Supabase Integration (conditional)
    if settings.enable_supabase and settings.supabase:
        # settings.supabase exists → config is valid
        supabase_manager = SupabaseManager(...)
        add_supabase_tools(mcp, supabase_manager)
    elif settings.enable_supabase and not settings.supabase:
        # Enable flag is True, but config is invalid
        logger.warning("Supabase enabled but invalid config")
    else:
        # Supabase disabled
        logger.debug("Supabase disabled")
    
    # 4. Start server
    await mcp.run_async(...)
```

## Configuration Precedence

For all settings, precedence is (highest first):

1. **CLI arguments** (`--enable-supabase`, `--supabase-url`, etc.)
2. **Environment variables** (`IQ_ENABLE_SUPABASE`, `IQ_SUPABASE_URL`, etc.)
3. **Backward-compat env vars** (`SUPABASE_URL`, `SUPABASE_KEY`)
4. **Defaults** (usually `False` or `None`)

## Examples

### Example 1: Supabase Disabled (Default)
```bash
python -m mcp_knowledge_graph
```

**Result:**
- `settings.supabase = None`
- `settings.enable_supabase = False`
- No Supabase tools registered
- No Supabase imports loaded

### Example 2: Supabase Enabled via CLI
```bash
python -m mcp_knowledge_graph \
    --enable-supabase \
    --supabase-url https://xxx.supabase.co \
    --supabase-key xxxxx
```

**Result:**
- `settings.supabase` = `SupabaseConfig(enabled=True, url=..., key=...)`
- `settings.enable_supabase = True`
- Supabase tools registered
- Supabase manager initialized

### Example 3: Supabase Enabled via Env Vars
```bash
export IQ_ENABLE_SUPABASE=true
export IQ_SUPABASE_URL=https://xxx.supabase.co
export IQ_SUPABASE_KEY=xxxxx
python -m mcp_knowledge_graph
```

**Result:**
- Same as Example 2

### Example 4: Enabled but Invalid Config
```bash
python -m mcp_knowledge_graph --enable-supabase
# (missing URL/key)
```

**Result:**
- `settings.enable_supabase = True`
- `settings.supabase = None` (invalid config)
- Warning logged: "Supabase enabled but configuration is invalid"
- No Supabase tools registered

## Benefits of This Pattern

1. **Separation of Concerns**: Core settings separate from integrations
2. **Extensibility**: Easy to add more integrations (Redis, Postgres, etc.)
3. **Backward Compatible**: Existing code using `settings.debug` still works
4. **Validation**: Invalid configs are caught early
5. **Lazy Loading**: Integration configs only loaded if enabled
6. **Clean API**: `settings.supabase.url` vs `settings.supabase_url`

## Future Extensibility

To add a new integration (e.g., Redis):

1. Create `RedisConfig` class (similar to `SupabaseConfig`)
2. Add to `Settings.load()`:
   ```python
   redis_config = RedisConfig.load(dry_run=core.dry_run)
   redis = redis_config if redis_config.is_valid() else None
   ```
3. Add to `Settings.__init__()`:
   ```python
   def __init__(self, *, core: IQSettings, supabase: SupabaseConfig | None = None,
                redis: RedisConfig | None = None):
       self.core = core
       self.supabase = supabase
       self.redis = redis
   ```

The pattern scales cleanly without bloating the core settings class.

