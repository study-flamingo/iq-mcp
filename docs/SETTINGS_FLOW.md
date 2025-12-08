# Settings and Initialization Flow

This document explains how settings and initialization work with the context-based architecture.

## Architecture Overview

The application uses a **context pattern** to manage runtime state:

1. **`version.py`**: Pure constants (`IQ_MCP_VERSION`, `IQ_MCP_SCHEMA_VERSION`)
2. **`settings.py`**: Configuration classes (no module-level side effects)
   - `IQSettings`: Core application settings
   - `SupabaseConfig`: Optional Supabase integration settings
   - `AppSettings`: Composition class combining core + integrations
3. **`context.py`**: Runtime state container (`AppContext`)
   - Holds initialized settings, logger, and optional Supabase manager
   - Singleton pattern; initialized once at startup via `ctx.init()`

## Initialization Flow

### Step 1: Entry Point (`__main__.py`)

```python
from .context import ctx
from .server import start_server

def main():
    ctx.init()  # Initialize context first
    logger.info(f"Memory path: {ctx.settings.memory_path}")
    asyncio.run(start_server())
```

### Step 2: Context Initialization (`ctx.init()`)

```python
ctx.init()
├── AppSettings.load()           # Load all settings
│   ├── IQSettings.load()        # Core settings from CLI/env/defaults
│   │   ├── Parse CLI args
│   │   ├── Load .env file
│   │   └── Apply defaults
│   │
│   └── SupabaseConfig.load()    # Optional Supabase settings
│       ├── Check enable flag
│       ├── Load URL/key
│       └── Validate config
│
├── Configure logger             # Set up logging based on settings
│
└── Initialize Supabase          # Only if enabled and valid
    └── SupabaseManager(config)
```

### Step 3: Server Startup (`start_server()`)

```python
async def start_server():
    ctx.init()  # Idempotent; safe to call again
    settings = ctx.settings
    
    _init_manager()  # Create KnowledgeGraphManager
    
    # Configure transport
    validated_transport = settings.transport
    
    # Startup checks
    await startup_check()
    
    # Add Supabase tools if enabled
    if settings.supabase_enabled:
        add_supabase_tools(mcp)
    
    # Run server
    await mcp.run_async(transport=validated_transport, ...)
```

## Context Structure

```python
ctx: AppContext
├── settings: AppSettings
│   ├── core: IQSettings
│   │   ├── debug: bool
│   │   ├── transport: Transport
│   │   ├── port: int
│   │   ├── memory_path: str
│   │   ├── streamable_http_host: str | None
│   │   ├── streamable_http_path: str | None
│   │   ├── project_root: Path
│   │   ├── no_emojis: bool
│   │   └── dry_run: bool
│   │
│   └── supabase: SupabaseConfig | None
│       ├── enabled: bool
│       ├── url: str | None
│       ├── key: str | None
│       ├── dry_run: bool
│       └── table names...
│
├── logger: logging.Logger
│
└── supabase: SupabaseManager | None
```

## Accessing Settings

Throughout the application, use the context:

```python
from .context import ctx

# After ctx.init() is called:
ctx.settings.debug           # Core setting
ctx.settings.memory_path     # Core setting (convenience property)
ctx.settings.supabase_enabled  # Check if Supabase is active
ctx.supabase                 # SupabaseManager instance (or None)
ctx.logger                   # Configured logger
```

## Lazy Logger

The `iq_logging` module provides a lazy logger that works before and after initialization:

```python
from .iq_logging import logger

# Before ctx.init(): uses bootstrap logger (stderr)
# After ctx.init(): uses ctx.logger (file + configured level)
logger.info("This works at any time")
```

## Configuration Precedence

For all settings, precedence is (highest first):

1. **CLI arguments** (`--enable-supabase`, `--supabase-url`, etc.)
2. **Environment variables** (`IQ_ENABLE_SUPABASE`, `IQ_SUPABASE_URL`, etc.)
3. **Defaults** (usually `False` or `None`)

## Examples

### Example 1: Supabase Disabled (Default)

```bash
python -m mcp_knowledge_graph
```

**Result:**
- `ctx.settings.supabase = None`
- `ctx.settings.supabase_enabled = False`
- `ctx.supabase = None`
- No Supabase tools registered

### Example 2: Supabase Enabled via CLI

```bash
python -m mcp_knowledge_graph \
    --enable-supabase \
    --supabase-url https://xxx.supabase.co \
    --supabase-key xxxxx
```

**Result:**
- `ctx.settings.supabase` = `SupabaseConfig(enabled=True, ...)`
- `ctx.settings.supabase_enabled = True`
- `ctx.supabase` = `SupabaseManager` instance
- Supabase tools registered

### Example 3: Supabase Enabled via Env Vars

```bash
export IQ_ENABLE_SUPABASE=true
export IQ_SUPABASE_URL=https://xxx.supabase.co
export IQ_SUPABASE_KEY=xxxxx
python -m mcp_knowledge_graph
```

**Result:** Same as Example 2

### Example 4: Enabled but Invalid Config

```bash
python -m mcp_knowledge_graph --enable-supabase
# (missing URL/key)
```

**Result:**
- `ctx.settings.supabase = None` (config invalid)
- `ctx.supabase = None`
- Warning logged
- No Supabase tools registered

## Benefits of This Pattern

1. **No import-time side effects**: Settings classes don't execute code on import
2. **Explicit initialization**: `ctx.init()` is called once at a known point
3. **Testability**: Can initialize context with different settings for tests
4. **Separation of concerns**: Config classes vs runtime state vs business logic
5. **Lazy dependencies**: Supabase only initialized if enabled
6. **Clean dependency injection**: Manager and tools access deps via `ctx`

## Adding New Integrations

To add a new integration (e.g., Redis):

1. Create `RedisConfig` class in `settings.py`:
   ```python
   class RedisConfig:
       def __init__(self, *, enabled: bool, url: str | None, ...): ...
       
       @classmethod
       def load(cls, dry_run: bool = False) -> "RedisConfig | None": ...
       
       def is_valid(self) -> bool: ...
   ```

2. Add to `AppSettings`:
   ```python
   class AppSettings:
       def __init__(self, *, core, supabase=None, redis=None):
           self.core = core
           self.supabase = supabase
           self.redis = redis
   ```

3. Initialize in `context.py`:
   ```python
   if self._settings.redis_enabled and self._settings.redis:
       self._redis = RedisManager(self._settings.redis)
   ```

The pattern scales cleanly without bloating any single module.
