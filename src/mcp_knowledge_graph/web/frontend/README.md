# IQ-MCP Graph Visualizer Frontend

Interactive React-based knowledge graph visualizer with editing capabilities.

## Features

- **Interactive Graph Canvas** - Pan, zoom, and explore your knowledge graph
- **Multiple Layouts** - Force-directed, circular, grid, hierarchical, and concentric
- **Entity Management** - Create, edit, and delete entities
- **Relation Management** - Create and delete relations between entities
- **Search & Filter** - Search across nodes and observations
- **Inspector Panel** - View and edit node/edge details
- **JWT Authentication** - Secure access via API token

## Development

### Prerequisites

- Node.js 18+
- npm or yarn

### Setup

```bash
# Install dependencies
npm install

# Start development server (with hot reload)
npm run dev

# Build for production
npm run build
```

### Development Server

The development server runs on `http://localhost:5173` with a proxy to the backend API at `http://localhost:8000/api`.

### Build

The production build outputs to `../static/` directory, which is served by the Python backend.

```bash
npm run build
```

## Usage

### Authentication

The app requires a JWT token to access the API. Provide it via URL parameter:

```
http://your-domain.com/graph?token=YOUR_API_KEY
```

The token will be saved to `localStorage` and the URL will be cleaned up.

### Graph Visualizer Features

1. **Pan/Zoom** - Click and drag to pan, scroll to zoom
2. **Select Node** - Click on a node to view details in the inspector panel
3. **Select Edge** - Click on an edge to view relation details
4. **Create Entity** - Click "+ Entity" button in toolbar
5. **Create Relation** - Click "+ Relation" button in toolbar
6. **Edit Entity** - Select a node, then click "Edit" in the inspector
7. **Delete Entity/Relation** - Select and click "Delete"
8. **Search** - Type in the search box to filter nodes
9. **Change Layout** - Use the layout dropdown to switch visualization modes

### Keyboard Shortcuts

- **Escape** - Deselect current selection
- **Ctrl/Cmd + F** - Focus search box

## Architecture

```
src/
├── components/
│   ├── GraphCanvas.jsx      # Cytoscape visualization
│   ├── InspectorPanel.jsx   # Details panel
│   ├── EntityForm.jsx       # Entity create/edit form
│   ├── RelationForm.jsx     # Relation create form
│   └── Toolbar.jsx          # Top toolbar with controls
├── api/
│   └── graphApi.js          # API client
├── styles/
│   ├── index.css            # Global styles
│   ├── App.css              # App layout
│   ├── Toolbar.css          # Toolbar styles
│   ├── InspectorPanel.css   # Inspector panel styles
│   └── Forms.css            # Form styles
├── App.jsx                  # Main app component
└── main.jsx                 # Entry point
```

## Customization

### Color Scheme

Edit `src/styles/index.css` to customize the color scheme:

```css
:root {
  --bg-primary: #0f172a;      /* Dark background */
  --accent-blue: #60a5fa;      /* Primary accent */
  /* ... */
}
```

### Node Styling

Edit `src/components/GraphCanvas.jsx` to customize node appearance:

```javascript
{
  selector: 'node',
  style: {
    'background-color': '#60a5fa',
    'width': (node) => Math.max(30, 15 + (node.data('observation_count') || 0) * 2),
    // ...
  }
}
```

### Layouts

Available layouts in Cytoscape:
- `cola` - Force-directed (default)
- `circle` - Circular layout
- `grid` - Grid layout
- `breadthfirst` - Hierarchical layout
- `concentric` - Concentric circles

### Adding Custom Extensions

If you want to add more Cytoscape extensions (e.g., `cytoscape-dagre` for different layouts):

```bash
npm install cytoscape-dagre
```

Then in `GraphCanvas.jsx`:

```javascript
import dagre from 'cytoscape-dagre';

// Always check before registering to avoid hot-reload errors
if (typeof cytoscape('core', 'dagre') !== 'function') {
  cytoscape.use(dagre);
}
```

**Important**: Always use the conditional check pattern to prevent "already exists in the prototype" errors during development with hot module replacement.

## Deployment

### Production Build

```bash
cd src/mcp_knowledge_graph/web/frontend
npm install
npm run build
```

The build outputs to `../static/`, which is automatically served by the Python backend when accessed at `/graph`.

### Docker

The frontend build can be integrated into your Docker image:

```dockerfile
# Install Node.js in your Docker image
RUN apt-get update && apt-get install -y nodejs npm

# Build frontend
WORKDIR /app/src/mcp_knowledge_graph/web/frontend
RUN npm install && npm run build
```

## Troubleshooting

### "Authentication failed"

Make sure you've set `IQ_API_KEY` or `IQ_GRAPH_JWT_TOKEN` in your `.env` file and provided it in the URL:

```
?token=YOUR_API_KEY
```

### "Frontend Not Built"

Run `npm run build` in the frontend directory before starting the server.

### CORS Issues

If developing locally, the Vite dev server proxies API requests to `localhost:8000`. Update `vite.config.js` if your backend runs on a different port.

### Cytoscape Extension Registration Errors

**Error**: `Can not register [extension] for core since [extension] already exists in the prototype`

**Cause**: This occurs when Cytoscape extensions are registered multiple times during hot module replacement (HMR) in development.

**Solution**: Already implemented! The code checks if extensions are registered before calling `cytoscape.use()`:

```javascript
// In GraphCanvas.jsx
if (typeof cytoscape('core', 'cola') !== 'function') {
  cytoscape.use(cola);
}
```

If you add new extensions, always use this pattern to avoid duplicate registration errors.

**References**:
- [Cytoscape.js Issue #2887](https://github.com/cytoscape/cytoscape.js/issues/2887)
- [Extension Registration Issue #1585](https://github.com/cytoscape/cytoscape.js/issues/1585)

## License

Same as parent project (Non-Commercial License)
