# Changelog

All notable changes to IQ-MCP will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Interactive Graph Visualizer** - Web-based UI for exploring and editing the knowledge graph
  - React + Cytoscape.js powered interface accessible at `/graph` endpoint
  - Full CRUD operations for entities and relations
  - Multiple layout options (force-directed, circular, grid, hierarchical, concentric)
  - Search and filter functionality across nodes and observations
  - Inspector panel for viewing and editing node/edge details
  - JWT authentication for secure access
  - Obsidian.md-inspired dark theme UI
  - Pan/zoom controls and interactive graph canvas
- Web module (`src/mcp_knowledge_graph/web/`) with FastAPI routes
- REST API endpoints for graph operations
- Comprehensive visualizer documentation (VISUALIZER.md)

### Fixed
- Cytoscape extension registration check to prevent "already exists in the prototype" errors during React hot module replacement
- Duplicate extension registration during development with conditional check before `cytoscape.use()`

### Changed
- Modified `server.py` to mount web UI alongside MCP endpoints using Starlette when `IQ_TRANSPORT=http`
- Updated main README.md to highlight new visualizer feature
- Enhanced development documentation with Cytoscape best practices

## [1.4.1] - 2025-12-19

(Previous changelog entries remain unchanged...)
