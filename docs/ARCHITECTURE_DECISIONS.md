# Architecture Decision Records (ADR)

This document records important architectural decisions made for the IQ-MCP Knowledge Graph Server project.

## What is an ADR?

An Architecture Decision Record is a document that captures an important architectural decision made along with its context and consequences. ADRs help maintain institutional knowledge and provide rationale for design choices.

## ADR Format

Each ADR follows this structure:

- **Status**: Proposed | Accepted | Deprecated | Superseded
- **Context**: The issue motivating this decision
- **Decision**: The change that we're proposing or have agreed to implement
- **Consequences**: What becomes easier or more difficult to do because of this change

---

## ADR-001: JSONL as Primary Storage Format

**Status**: Accepted  
**Date**: 2024 (Initial design)  
**Deciders**: Project maintainers

### Context

The knowledge graph needs a simple, portable, and human-readable storage format that:
- Works across all platforms (Windows, macOS, Linux)
- Is easy to backup and version control
- Supports incremental writes
- Doesn't require a database server for basic operation

### Decision

Use JSONL (JSON Lines) format as the primary storage mechanism. Each line is a complete JSON object representing a single graph element (entity, relation, observation, metadata, or user info).

### Consequences

**Positive**:
- ✅ No database server required for basic operation
- ✅ Human-readable and easy to debug
- ✅ Easy to backup (just copy the file)
- ✅ Version control friendly (line-by-line diffs)
- ✅ Portable across platforms
- ✅ Supports streaming writes (append-only)
- ✅ Simple to parse and validate

**Negative**:
- ❌ No built-in querying (must load entire graph for searches)
- ❌ No transactions (but mitigated by atomic writes)
- ❌ Linear scan required for lookups (acceptable for typical graph sizes)
- ❌ No concurrent write safety (single-user assumption)

**Mitigations**:
- Supabase integration provides cloud storage and querying when needed
- Daily automatic backups to `backups/` subdirectory
- Schema versioning enables safe migrations

---

## ADR-002: Pydantic v2 for Data Validation

**Status**: Accepted  
**Date**: 2024 (Initial design)  
**Deciders**: Project maintainers

### Context

The knowledge graph needs strict data validation to ensure:
- Type safety across the codebase
- Runtime validation of user inputs
- Clear error messages for invalid data
- Serialization/deserialization consistency

### Decision

Use Pydantic v2 models for all data structures (Entity, Relation, Observation, UserIdentifier, etc.).

### Consequences

**Positive**:
- ✅ Strong type safety with Python type hints
- ✅ Automatic validation of inputs
- ✅ Clear error messages for invalid data
- ✅ JSON serialization/deserialization built-in
- ✅ Field validation and computed fields
- ✅ Model validators for complex validation rules

**Negative**:
- ❌ Additional dependency (but widely used and stable)
- ❌ Slight performance overhead (negligible for typical use cases)

---

## ADR-003: FastMCP as MCP Server Framework

**Status**: Accepted  
**Date**: 2024 (Initial design)  
**Deciders**: Project maintainers

### Context

The project needs an MCP (Model Context Protocol) server implementation that:
- Supports HTTP transport for cloud deployment
- Provides authentication mechanisms
- Has good documentation and community support
- Enables async operations
- Supports stateless operation for scalability

### Decision

Use FastMCP 2.13+ as the MCP server framework.

### Consequences

**Positive**:
- ✅ Built-in HTTP transport support
- ✅ Authentication support (StaticTokenVerifier)
- ✅ Stateless HTTP mode for Cursor compatibility
- ✅ Async/await support
- ✅ Clean decorator-based tool definition
- ✅ Active development and good documentation

**Negative**:
- ❌ Framework dependency (but well-maintained)
- ❌ Must stay compatible with FastMCP API changes

---

## ADR-004: Optional Supabase Integration

**Status**: Accepted  
**Date**: 2024 (Initial design)  
**Deciders**: Project maintainers

### Context

Users may want:
- Cloud synchronization across devices
- Email integration capabilities
- Query capabilities beyond linear scan
- Backup redundancy

But the core should work without any external services.

### Decision

Make Supabase integration optional. Core functionality works with local JSONL only. Supabase provides:
- Cloud storage sync
- Email summary integration
- Query capabilities
- Multi-device support

### Consequences

**Positive**:
- ✅ Core works everywhere without dependencies
- ✅ Users can opt-in to cloud features
- ✅ No vendor lock-in for basic usage
- ✅ Progressive enhancement model

**Negative**:
- ❌ Two code paths (local vs Supabase)
- ❌ Must maintain sync logic
- ❌ Additional complexity in manager layer

**Mitigations**:
- Clear separation between local and Supabase code paths
- Graceful degradation when Supabase is disabled
- Comprehensive error handling

---

## ADR-005: Stateless HTTP Mode for Cursor Compatibility

**Status**: Accepted  
**Date**: December 2024  
**Deciders**: Project maintainers

### Context

Cursor MCP client requires stateless HTTP operation. Without this, clients receive "No valid session ID" errors when making tool calls.

### Decision

Enable `FASTMCP_STATELESS_HTTP=true` for all HTTP deployments. This makes the server stateless, with each request being independent.

### Consequences

**Positive**:
- ✅ Works with Cursor MCP client
- ✅ Better scalability (no session state)
- ✅ Simpler deployment (no session management)

**Negative**:
- ❌ No session-based state (but not needed for current use case)
- ❌ Each request must be self-contained

**Mitigations**:
- All state stored in JSONL/Supabase (persistent)
- No in-memory session state required

---

## ADR-006: Entity ID Format (8-character alphanumeric)

**Status**: Accepted  
**Date**: 2024 (Initial design)  
**Deciders**: Project maintainers

### Context

Entities need unique identifiers that are:
- Human-readable
- Short enough to be manageable
- Collision-resistant
- Easy to reference in relations

### Decision

Use 8-character alphanumeric IDs (EntityID type). Generated using a collision-resistant algorithm.

### Consequences

**Positive**:
- ✅ Short and readable
- ✅ Easy to reference in relations
- ✅ Sufficient uniqueness for typical graph sizes
- ✅ Validated via Pydantic model

**Negative**:
- ❌ Potential collisions at very large scale (10M+ entities)
- ❌ Not globally unique (but fine for single-user graphs)

**Mitigations**:
- Collision detection and retry logic
- For multi-user scenarios, consider longer IDs or UUIDs (future)

---

## ADR-007: Temporal Observations with Durability Levels

**Status**: Accepted  
**Date**: 2024 (Initial design)  
**Deciders**: Project maintainers

### Context

Observations have different lifespans. Some are temporary (e.g., "currently working on X"), while others are permanent (e.g., "has a PhD in Computer Science").

### Decision

Implement durability levels for observations:
- `temporary`: 1 month
- `short-term`: 3 months
- `long-term`: 1 year
- `permanent`: never expires

Automatic cleanup removes expired observations based on their durability and timestamp.

### Consequences

**Positive**:
- ✅ Automatic memory management
- ✅ Prevents graph bloat from outdated information
- ✅ Clear semantic meaning for LLMs
- ✅ User control over observation lifespan

**Negative**:
- ❌ Information loss if durability is set incorrectly
- ❌ Requires timestamp tracking

**Mitigations**:
- Conservative defaults (short-term)
- User can set permanent for important facts
- Timestamps automatically added on creation

---

## ADR-008: Single-User Focus (No Multi-User Support)

**Status**: Accepted  
**Date**: 2024 (Initial design)  
**Deciders**: Project maintainers

### Context

The project could support multiple users or remain single-user focused. Multi-user support adds significant complexity (authentication, authorization, data isolation, conflict resolution).

### Decision

Focus on single-user use case. Each instance serves one user. Multi-user support deferred to v3.0.0+ if needed.

### Consequences

**Positive**:
- ✅ Simpler architecture
- ✅ No authentication/authorization complexity
- ✅ No data isolation needed
- ✅ Faster development
- ✅ Lower resource usage

**Negative**:
- ❌ Cannot share graphs between users
- ❌ No collaborative features
- ❌ Each user needs separate instance/deployment

**Future Considerations**:
- If multi-user is needed, can add user authentication layer
- Supabase already supports multi-tenancy if needed
- Graph structure supports user isolation (via UserIdentifier)

---

## ADR-009: Client Agnosticism Principle

**Status**: Accepted  
**Date**: 2024 (Initial design)  
**Deciders**: Project maintainers

### Context

MCP servers can be used by various clients (Claude Desktop, Cursor, Roo Code, custom clients). Each client may have different capabilities and requirements.

### Decision

Design all features to work identically across all MCP-compliant clients. No client-specific code paths or feature detection.

### Consequences

**Positive**:
- ✅ Works everywhere MCP is supported
- ✅ No client lock-in
- ✅ Easier maintenance (one codebase)
- ✅ Better user experience (consistent behavior)

**Negative**:
- ❌ Cannot use client-specific optimizations
- ❌ Must use lowest common denominator features
- ❌ May miss opportunities for client-specific enhancements

**Mitigations**:
- Use standard MCP features only
- Server generates data, clients render as they prefer
- Progressive enhancement where possible

---

## ADR-010: Version and Schema Version Separation

**Status**: Accepted  
**Date**: 2024 (Initial design)  
**Deciders**: Project maintainers

### Context

Application version changes (features, bug fixes) are independent of storage format changes. Need to track both separately for migration purposes.

### Decision

Maintain two separate version numbers:
- `IQ_MCP_VERSION`: Application version (Semantic Versioning)
- `IQ_MCP_SCHEMA_VERSION`: Storage format version (integer)

Schema version is stored in GraphMeta and used for migration logic.

### Consequences

**Positive**:
- ✅ Clear separation of concerns
- ✅ Safe migrations based on schema version
- ✅ Can add features without changing storage format
- ✅ Can change storage format without changing app version

**Negative**:
- ❌ Two version numbers to track
- ❌ Must increment schema version for storage changes

**Mitigations**:
- Clear documentation of when to increment each
- Migration helpers check schema version
- Backward compatibility maintained for at least 2 major versions

---

## ADR-011: Docker + Nginx Deployment Architecture

**Status**: Accepted  
**Date**: December 2024  
**Deciders**: Project maintainers

### Context

The server needs to be deployed to production with:
- SSL/TLS termination
- Reverse proxy capabilities
- Containerization for easy deployment
- Stateless HTTP operation

### Decision

Use Docker containerization with nginx as reverse proxy:
- Docker container runs FastMCP server on port 8000
- Nginx handles SSL termination and proxies `/iq` → `/mcp`
- Let's Encrypt for SSL certificates
- Docker Compose for orchestration

### Consequences

**Positive**:
- ✅ Easy deployment and scaling
- ✅ SSL handled by nginx (industry standard)
- ✅ Container isolation
- ✅ Easy to update (pull new image)
- ✅ Works on any Docker host

**Negative**:
- ❌ Additional infrastructure (nginx container)
- ❌ SSL certificate management (but automated via certbot)
- ❌ More complex than single-process deployment

**Mitigations**:
- Automated SSL renewal via certbot
- Docker Compose simplifies orchestration
- Clear deployment documentation

---

## Future ADRs

As new architectural decisions are made, they should be added to this document following the same format.

### Proposed Topics for Future ADRs

- ADR-012: Flexible Tool Parameters for Token Efficiency (v1.7.0)
- ADR-013: Project/Task Management Data Model (v1.5.0)
- ADR-014: Semantic Search Implementation Strategy (v1.6.0)
- ADR-015: Multi-Device Sync Strategy (v2.0.0)

---

## References

- [ADR Template](https://adr.github.io/)
- [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
