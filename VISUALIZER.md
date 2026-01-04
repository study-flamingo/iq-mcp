# Graph Visualizer Setup Guide

This document explains how to set up and use the interactive graph visualizer for IQ-MCP.

## Overview

The graph visualizer provides a web-based interface for viewing and editing your knowledge graph. It features:

- 🎨 **Interactive Canvas** - Pan, zoom, and explore your graph
- 🎯 **Multiple Layouts** - Force-directed, circular, hierarchical, and more
- ✏️ **Full Editing** - Create, update, and delete entities and relations
- 🔍 **Search & Filter** - Find nodes and observations instantly
- 🎭 **Obsidian-like UI** - Inspired by Obsidian.md's graph view
- 🔐 **Secure** - JWT authentication for all operations

## Quick Start

### 1. Build the Frontend

```bash
cd src/mcp_knowledge_graph/web/frontend
npm install
npm run build
```

This builds the React app and outputs it to `src/mcp_knowledge_graph/web/static/`.

### 2. Set Up Authentication

Add your API key to `.env`:

```bash
# Use existing API key
IQ_API_KEY=your-api-key-here

# Or create a separate token for the web UI
IQ_GRAPH_JWT_TOKEN=your-web-token-here
```

### 3. Start the Server

```bash
# HTTP transport is required for the web UI
IQ_TRANSPORT=http python -m mcp_knowledge_graph
```

The server will start on `http://localhost:8000`.

### 4. Access the Visualizer

Open your browser and navigate to:

```
http://localhost:8000/graph?token=YOUR_API_KEY
```

Replace `YOUR_API_KEY` with the value from your `.env` file.

## Deployment to Production

### On Your Google Cloud VM

1. **Build the frontend** (can be done locally):
   ```bash
   cd src/mcp_knowledge_graph/web/frontend
   npm install
   npm run build
   ```

2. **Push to your VM** using your existing deployment script:
   ```bash
   ./deploy/push-and-deploy.sh
   ```

3. **Configure nginx** to proxy `/graph` to your app (if not already done):
   ```nginx
   location / {
       proxy_pass http://localhost:8000;
       proxy_set_header Host $host;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

4. **Access via your domain**:
   ```
   https://your-domain.com/graph?token=YOUR_API_KEY
   ```

## Usage Guide

### Creating Entities

1. Click **"+ Entity"** in the toolbar
2. Fill in the form:
   - **Name**: Entity identifier (e.g., "John_Doe")
   - **Type**: person, organization, event, concept, etc.
   - **Icon**: Single emoji (e.g., 👤)
   - **Aliases**: Alternative names (comma-separated)
   - **Observations**: Add facts with durability levels
3. Click **"Create"**

### Creating Relations

1. Click **"+ Relation"** in the toolbar
2. Select **from entity** and **to entity**
3. Enter the **relation** in active voice (e.g., "works at", "manages")
4. Click **"Create Relation"**

### Editing Entities

1. Click on a node in the graph
2. View details in the **inspector panel** (right side)
3. Click **"Edit"** to modify properties
4. Save changes

### Deleting

- **Entities**: Select node → Click "Delete" in inspector
- **Relations**: Select edge → Click "Delete Relation"

### Search & Filter

- **Search box**: Type to filter nodes by name, type, or observation content
- **Layout dropdown**: Switch between visualization modes:
  - Force (Cola) - Default, organic clustering
  - Circle - Nodes arranged in a circle
  - Grid - Structured grid layout
  - Hierarchy - Tree-like structure
  - Concentric - Concentric circles by importance

### Keyboard Shortcuts

- **Escape**: Clear selection
- **Ctrl/Cmd + F**: Focus search box
- **Click + Drag**: Pan the canvas
- **Scroll**: Zoom in/out

## API Endpoints

The visualizer uses these REST API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/graph` | Serve the React app |
| GET | `/api/graph/data` | Fetch complete graph data |
| POST | `/api/graph/entity` | Create new entity |
| PATCH | `/api/graph/entity/:id` | Update entity |
| DELETE | `/api/graph/entity/:id` | Delete entity |
| POST | `/api/graph/relation` | Create relation |
| DELETE | `/api/graph/relation` | Delete relation |
| POST | `/api/graph/entity/:id/observations` | Add observations |

All endpoints require `Authorization: Bearer YOUR_API_KEY` header.

## Customization

### Change Colors

Edit `src/mcp_knowledge_graph/web/frontend/src/styles/index.css`:

```css
:root {
  --accent-blue: #60a5fa;
  --accent-green: #34d399;
  /* ... customize colors ... */
}
```

Then rebuild: `npm run build`

### Add Custom Layouts

Edit `src/mcp_knowledge_graph/web/frontend/src/components/Toolbar.jsx` to add more layout options.

### Modify Node Styling

Edit `src/mcp_knowledge_graph/web/frontend/src/components/GraphCanvas.jsx` to customize node appearance based on entity types, observation counts, etc.

## Troubleshooting

### "Frontend Not Built" Error

**Solution**: Run the build command:
```bash
cd src/mcp_knowledge_graph/web/frontend
npm run build
```

### Authentication Errors

**Problem**: "Invalid authentication token" or 401 errors

**Solutions**:
1. Make sure `IQ_API_KEY` is set in `.env`
2. Include `?token=YOUR_API_KEY` in the URL
3. Clear browser localStorage and try again

### Graph Not Loading

**Problem**: Empty graph or loading forever

**Solutions**:
1. Check browser console for errors (F12)
2. Verify your memory file exists and is valid
3. Check server logs for backend errors
4. Try accessing `/api/graph/data` directly to test the API

### Changes Not Saving

**Problem**: Edits don't persist after refresh

**Solutions**:
1. Check that `IQ_DRY_RUN` is not set to `true`
2. Verify file permissions on `memory.jsonl`
3. Check server logs for save errors

### CORS Errors (Development)

**Problem**: Cross-origin errors when developing

**Solution**: The Vite dev server proxies API requests. Make sure your backend is running on port 8000, or update `vite.config.js`:

```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:YOUR_PORT',
      changeOrigin: true,
    }
  }
}
```

## Architecture

```
┌─────────────────────────────────────────┐
│  Browser (React + Cytoscape.js)         │
│  https://your-domain.com/graph          │
└─────────────────────────────────────────┘
              ↓ HTTPS + JWT
┌─────────────────────────────────────────┐
│  Nginx (SSL + Reverse Proxy)            │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  FastMCP + Starlette Server             │
│  ├─ /graph → React App                  │
│  ├─ /api/graph/* → REST API             │
│  └─ /mcp → MCP Protocol                 │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  KnowledgeGraphManager                  │
│  (Existing business logic)              │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Supabase + Local JSONL                 │
└─────────────────────────────────────────┘
```

## Development Workflow

### Local Development

1. **Terminal 1** - Run the backend:
   ```bash
   IQ_TRANSPORT=http python -m mcp_knowledge_graph
   ```

2. **Terminal 2** - Run the frontend dev server:
   ```bash
   cd src/mcp_knowledge_graph/web/frontend
   npm run dev
   ```

3. Access at `http://localhost:5173` (auto-reloads on changes)

### Production Build

```bash
# Build frontend
cd src/mcp_knowledge_graph/web/frontend
npm run build

# Deploy (your existing script)
./deploy/push-and-deploy.sh
```

## Next Steps

- **Add more entity types**: Edit the dropdown in `EntityForm.jsx`
- **Customize graph appearance**: Modify `GraphCanvas.jsx` styles
- **Add analytics**: Show graph statistics (node count, relation count, etc.)
- **Batch operations**: Select multiple nodes for bulk edit/delete
- **Export**: Add export to PNG, SVG, or JSON
- **Time-travel**: Add historical view of graph state
- **AI features**: Integrate LLM suggestions for relations

## Support

For issues or questions:
1. Check server logs: Look for errors in terminal output
2. Check browser console: Press F12 to see frontend errors
3. Review API responses: Use browser DevTools Network tab
4. Create an issue on GitHub if you find bugs

---

**Enjoy your interactive knowledge graph!** 🎉
