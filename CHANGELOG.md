# Changelog

All notable changes to the IQ-MCP Knowledge Graph Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2025-12-19

### ✨ Enhanced Features

- **Flexible Entity References**: All CRUD tools now support referencing entities by either ID or name/alias
  - `create_relations`: Accepts entity names or IDs for both `from` and `to` endpoints
  - `delete_relations`: Supports name/ID resolution for relation endpoints
  - `merge_entities`: Accepts names, aliases, or IDs for entities to merge
  - Added `_resolve_entity_identifier()` helper method for consistent entity resolution

- **Enhanced `update_user_info` Tool**: Now supports adding observations in the same call
  - New optional `observations` parameter
  - Automatically adds observations to user-linked entity after updating user info
  - Returns summary of both operations

- **Enhanced `read_graph` Tool**: Added project awareness (placeholder for v1.5.0)
  - Shows active projects count
  - Displays most recently accessed project
  - Gracefully handles absence of project management (no errors if not implemented)

### 🔧 Improvements

- **Model Validation**: Added `model_validator` to ensure at least one identifier is provided
  - `CreateRelationRequest`: Requires either `from_entity_id` or `from_entity_name` (and same for `to`)
  - `ObservationRequest`: Requires either `entity_id` or `entity_name`
- **Better Error Messages**: Clearer errors when entities cannot be resolved
- **Consistent API**: All entity reference operations now work the same way

### 🧪 Testing

- Added 10 new tests for v1.4.0 features
- All 21 tests passing
- Maintained 100% backward compatibility

### 📚 Documentation

- Updated tool docstrings to reflect new capabilities
- Added validation requirements to model documentation

## [1.3.1] - 2025-12-19

### 🐛 Bug Fixes

- **Fixed `UpdateEntityRequest` model**: Fields were incorrectly wrapped in tuples instead of being `Field` objects
- **Fixed `update_entity` server function**: Now correctly extracts identifier from the `identifiers` list
- **Fixed `CreateEntityResult` type error**: Duplicate entity errors now return the existing `Entity` instead of the request
- **Fixed Supabase timestamp serialization**: Now uses `isoformat()` for PostgreSQL compatibility

### 🚀 Deployment

- **Registry-based deployment**: New workflow using Google Artifact Registry instead of scp + rebuild
- **`deploy/push-image.sh`**: Build and push Docker image to Artifact Registry
- **`deploy/pull-and-deploy.sh`**: Pull latest image and restart on VM
- **`deploy/push-and-deploy.sh`**: One-command full deployment
- **`docker-compose.prod.yml`**: Production compose file using registry images

### 🧪 Testing

- **Fixed test fixture**: Now uses `AppSettings` with proper logger initialization
- **All 11 unit tests passing**

### 📚 Documentation

- Updated `AGENTS.md` with new deployment workflow
- Updated `README.md` with production deployment section
- Updated `docs/files.md` with deploy script descriptions
- Added camelCase table name warning to `docs/SUPABASE_SCHEMA.md`

## [1.3.0] - 2025-12-07

### 🚀 Deployment & Authentication

- **HTTP deployment stack**: Added Docker + nginx deployment with SSL termination
- **API key authentication**: New `StaticTokenVerifier` support via `auth.py` module
- **Stateless HTTP mode**: `FASTMCP_STATELESS_HTTP=true` for Cursor/client compatibility
- **URL token auth**: nginx configured to accept `?token=` query parameter
- **Supabase as core dependency**: Moved from optional `[sb]` group to main dependencies

### 🏗️ Architecture

- **Context-based initialization**: Introduced `AppContext` singleton in `context.py` that manages runtime state (settings, logger, Supabase manager)
- **No import-time side effects**: Removed module-level `settings = AppSettings.load()` singleton; initialization now happens explicitly via `ctx.init()`
- **Centralized version constants**: Created `version.py` with `IQ_MCP_VERSION` and `IQ_MCP_SCHEMA_VERSION`
- **Decoupled models from settings**: `models.py` no longer imports `settings.py`; `Entity.icon_()` now accepts `use_emojis` parameter
- **Lazy logger**: `iq_logging.py` provides a proxy logger that works before and after context initialization

### 🆕 Added

- **`auth.py`**: Authentication provider configuration for HTTP deployments
- **`Dockerfile`**: Production Docker image with Python 3.13
- **`docker-compose.yml`**: Orchestration with nginx reverse proxy
- **`nginx/conf.d/mcp.conf`**: SSL termination and path routing
- **`deploy/` scripts**: `deploy.sh`, `quick-deploy.sh`, `vm-logs.sh`, `vm-ssh.sh`
- **Daily automatic backups**: Memory file is backed up daily to `backups/` subdirectory after each save
- **`context.py`**: New module for application context management
- **`version.py`**: New module for centralized version constants

### 🔄 Changed

- **FastMCP upgraded**: Now requires `>=2.13.0` for authentication support
- **Entry point flow**: `__main__.py` now calls `ctx.init()` before starting server
- **Manager initialization**: `KnowledgeGraphManager` uses `ctx` for dependencies instead of module-level imports
- **Server startup**: `start_server()` initializes context and manager explicitly
- **Supabase manager**: Removed redundant `load_dotenv()` call; configuration comes from context

### 📚 Documentation

- Updated all documentation in `docs/` to reflect new architecture
- New architecture diagrams and dependency flow documentation
- Updated `SETTINGS_FLOW.md` with context-based initialization details
- Added backup feature documentation
- Added `AGENTS.md` scratchpad for agent context

### 🛠️ Maintenance

- No storage schema changes; `IQ_MCP_SCHEMA_VERSION` remains 1
- Improved testability through explicit dependency injection

## [1.2.0] - 2025-11-17

### 🔄 Changed

- Project version aligned to 1.2.0 across codebase:
  - Updated `pyproject.toml` project version to 1.2.0
  - Updated `src/mcp_knowledge_graph/__init__.py` `__version__` to 1.2.0
  - Confirmed runtime `IQ_MCP_VERSION` is 1.2.0 in `settings.py`
- Normalized migration tool `CURRENT_VERSION` to `1.2.0` (no leading `v`)

### 🛠️ Maintenance

- Prepared for release PR to merge `dev` → `main`
- No storage schema changes; `IQ_MCP_SCHEMA_VERSION` remains 1

### 📚 References

- See `docs/PROJECT_OVERVIEW.md` (schema/versioning) and `docs/LLM_COLLAB.md` (semver & migrations).

## [0.7.0] - 2025-06-26

### 🆕 Added

- **Temporal Observation System**: Observations now support timestamp and durability metadata
- **Durability Categories**: Four levels - permanent, long-term, short-term, temporary
- **Smart Cleanup**: `cleanup_outdated_observations` tool for automatic removal of outdated information
- **Durability Querying**: `get_observations_by_durability` tool for categorized viewing
- **Enhanced TypeScript Interfaces**:
  - `TimestampedObservation` interface for temporal observations
  - `ObservationInput` interface for flexible observation creation
- **Automatic Normalization**: Legacy string observations converted to temporal format on load
- **Mixed Format Support**: `add_observations` accepts both strings and temporal objects

### 🔄 Changed

- **Enhanced `add_observations`**: Now supports temporal metadata while maintaining backward compatibility
- **Improved Error Handling**: Better error messages and type safety throughout
- **Updated Server Version**: Bumped to 0.7.0 to reflect temporal features
- **Comprehensive Documentation**: Updated README with temporal features and examples

### 🏗️ Technical Improvements

- **Type Safety**: Leveraged TypeScript string literal types for durability categories
- **Union Types**: Used for backward compatibility between string and temporal observations
- **Helper Methods**: Added private methods for observation creation and normalization
- **Data Migration**: Automatic conversion of legacy JSONL format to temporal format

### 📚 Documentation

- **Updated README**: Comprehensive documentation of temporal features
- **API Reference**: Detailed documentation of all tools and their capabilities
- **Usage Examples**: Practical examples showing temporal observation usage
- **System Prompt**: Enhanced memory prompt template leveraging temporal features
- **TypeScript Examples**: Demonstrated modern TypeScript patterns and best practices

### 🔒 Backward Compatibility

- **Legacy Support**: All existing string observations continue to work
- **Default Behavior**: String observations default to "long-term" durability
- **Automatic Migration**: JSONL files automatically converted without data loss
- **API Compatibility**: All existing tool signatures remain unchanged

## [0.6.3] - Base Version

### Original Features from Anthropic MCP Memory Server

- Basic entity/relation/observation CRUD operations
- Simple string-based search functionality
- JSONL storage format
- MCP protocol compliance
- Claude Desktop integration support

---

## Migration Guide

### From v1.3.1 to v1.4.0

**No action required!** The upgrade is fully backward compatible:

1. **Existing memory files**: Work without modification
2. **Existing tools**: Continue to work exactly as before
3. **New capabilities**: You can now use entity names or IDs interchangeably in all CRUD operations

**New features you can use**:

```python
# Create relations using names instead of IDs
create_relations([{
  "from_entity_name": "Alice",
  "to_entity_name": "Acme Corp",
  "relation": "works_at"
}])

# Merge entities using IDs
merge_entities(
  new_entity_name="John Smith",
  entity_identifiers=["a1b2c3d4", "e5f6g7h8"]  # IDs or names
)

# Update user info and add observations in one call
update_user_info(
  preferred_name="John",
  observations=[{
    "content": "prefers email communication",
    "durability": "long-term"
  }]
)
```

### From v1.2.0 to v1.3.0

**No action required!** The upgrade is fully backward compatible:

1. **Existing memory files**: Work without modification
2. **Existing tools**: Continue to work exactly as before
3. **New backups**: Will be created automatically in `backups/` subdirectory

**Architecture changes** (for developers extending the codebase):

- Import settings via `ctx.settings` instead of `from .settings import settings`
- Initialize context with `ctx.init()` before accessing `ctx.settings`, `ctx.logger`, or `ctx.supabase`
- Use `entity.icon_(use_emojis=True/False)` instead of relying on global settings

### From v0.6.3 to v0.7.0

**No action required!** The upgrade is fully backward compatible:

1. **Existing observations**: Automatically converted to temporal format with "long-term" durability
2. **Existing tools**: Continue to work exactly as before
3. **Data files**: Legacy JSONL files work without modification

**To leverage new features**:

```python
# Start using temporal observations
add_observations([{
  "entity_name": "user",
  "observations": [
    {"content": "Permanent fact", "durability": "permanent"},
    {"content": "Current project", "durability": "temporary"}
  ]
}])

# Clean up outdated information
cleanup_outdated_observations()

# View observations by category
get_observations_by_durability("user")
```

## Acknowledgments

This enhanced version builds upon the excellent foundation provided by Anthropic's original MCP Memory Server. The temporal observation system was designed and implemented by the author as part of exploring advanced knowledge management patterns for AI assistants.

## Contributing

Contributions are welcome! Please feel free to submit issues and enhancement requests.

## License

Non-Commercial License - see [LICENSE](LICENSE) file for details. Commercial use is prohibited.
