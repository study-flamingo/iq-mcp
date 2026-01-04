# Pull Request: Add Interactive Graph Visualizer with React and Cytoscape.js

## Summary

This PR adds a comprehensive web-based interactive graph visualizer for the IQ-MCP knowledge graph, accessible at `/graph` when HTTP transport is enabled.

## Features

### Interactive Graph Canvas
- **Pan/Zoom Controls** - Click and drag to pan, scroll to zoom
- **Multiple Layouts** - Force-directed (Cola), circular, grid, hierarchical, concentric
- **Visual Styling** - Color-coded by entity type, node size by observation count
- **Search & Filter** - Real-time search across nodes and observations

### Full CRUD Operations
- **Create Entities** - Form-based entity creation with observations
- **Edit Entities** - Update name, type, aliases, icon
- **Delete Entities** - Remove entities from the graph
- **Create Relations** - Connect entities with labeled edges
- **Delete Relations** - Remove connections

### Professional UI
- **Inspector Panel** - Right sidebar showing node/edge details
- **Toolbar** - Top bar with search, layout selector, and action buttons
- **Modal Forms** - Clean modals for creating entities and relations
- **Obsidian-Inspired** - Dark theme matching Obsidian.md aesthetics

### Technical Implementation
- **React + Vite** - Modern frontend with hot reload
- **Cytoscape.js** - Professional graph visualization library
- **FastAPI Integration** - REST API mounted alongside MCP endpoints
- **JWT Authentication** - Secure access using existing `IQ_API_KEY`

## Backend Changes

### New Web Module (`src/mcp_knowledge_graph/web/`)
- `routes.py` - FastAPI REST API endpoints
- `auth.py` - JWT authentication middleware
- Integrated with existing `KnowledgeGraphManager`

### Modified Files
- `server.py` - Mounts web UI alongside MCP using Starlette when `IQ_TRANSPORT=http`

### API Endpoints
- `GET /graph` - Serve React application
- `GET /api/graph/data` - Fetch complete graph data
- `POST /api/graph/entity` - Create entity
- `PATCH /api/graph/entity/:id` - Update entity
- `DELETE /api/graph/entity/:id` - Delete entity
- `POST /api/graph/relation` - Create relation
- `DELETE /api/graph/relation` - Delete relation
- `POST /api/graph/entity/:id/observations` - Add observations

## Frontend Architecture

```
frontend/
├── src/
│   ├── components/
│   │   ├── GraphCanvas.jsx      # Cytoscape visualization
│   │   ├── InspectorPanel.jsx   # Details sidebar
│   │   ├── EntityForm.jsx       # Create/edit entity form
│   │   ├── RelationForm.jsx     # Create relation form
│   │   └── Toolbar.jsx          # Top controls
│   ├── api/
│   │   └── graphApi.js          # API client with auth
│   └── styles/                   # CSS modules
├── package.json
└── vite.config.js
```

## Bug Fixes

### Cytoscape Extension Registration
- **Issue**: "Can not register cola for core since cola already exists in the prototype" during hot reload
- **Fix**: Conditional check before `cytoscape.use()` to prevent duplicate registration
- **Pattern**: `if (typeof cytoscape('core', 'cola') !== 'function') { cytoscape.use(cola); }`

## Documentation

### New Files
- `VISUALIZER.md` - Complete setup and usage guide
- `frontend/README.md` - Development documentation
- `CHANGELOG_VISUALIZER.md` - Feature changelog

### Updated Files
- `README.md` - Added visualizer to highlights, updated quick start

## Usage

### Setup
```bash
cd src/mcp_knowledge_graph/web/frontend
npm install
npm run build
```

### Run
```bash
IQ_TRANSPORT=http python -m mcp_knowledge_graph
```

### Access
```
http://localhost:8000/graph?token=YOUR_API_KEY
```

## Testing Checklist

- [x] Entity creation works
- [x] Entity editing saves correctly
- [x] Entity deletion removes from graph
- [x] Relation creation connects nodes
- [x] Relation deletion works
- [x] Search filters nodes correctly
- [x] Layout switching works
- [x] JWT authentication required
- [x] Hot reload works without Cytoscape errors
- [x] Graph refreshes after edits

## Breaking Changes

**None.** This is purely additive:
- MCP protocol unchanged
- Existing tools work exactly as before
- Web UI only available when `IQ_TRANSPORT=http`

## Dependencies

### Backend
No new Python dependencies (uses existing FastAPI from FastMCP)

### Frontend (dev only)
- react ^18.3.1
- cytoscape ^3.30.2
- cytoscape-cola ^2.5.1
- axios ^1.7.9
- vite ^6.0.3

Build outputs to `web/static/` which is served by Python backend.

## Deployment Notes

1. Build frontend before deploying: `cd frontend && npm run build`
2. No additional runtime dependencies (frontend is pre-built static files)
3. Works with existing Docker/nginx setup
4. Nginx should proxy `/graph` and `/api/graph/*` to backend

## Future Enhancements

Potential additions (not in this PR):
- Graph analytics dashboard
- Batch operations (select multiple nodes)
- Undo/redo functionality
- Export to PNG/SVG
- Time-travel view (historical graph states)
- Real-time collaboration via WebSockets

## Commits

- `276c4f8` - Add interactive graph visualizer with React and Cytoscape.js
- `2260056` - Fix: Prevent duplicate Cytoscape extension registration during hot reload
- `b8c6097` - docs: Update all documentation with Cytoscape fix and visualizer details

---

**Ready for review and merge!** This adds a powerful interactive visualizer while maintaining full backward compatibility with the existing MCP server.
