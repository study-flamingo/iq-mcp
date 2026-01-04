import { useState, useEffect } from 'react';
import GraphCanvas from './components/GraphCanvas';
import InspectorPanel from './components/InspectorPanel';
import Toolbar from './components/Toolbar';
import { graphApi } from './api/graphApi';
import './styles/App.css';

function App() {
  const [graphData, setGraphData] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [selectedEdge, setSelectedEdge] = useState(null);
  const [layout, setLayout] = useState('cola');
  const [filters, setFilters] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load graph data
  const loadGraph = async () => {
    try {
      setLoading(true);
      const data = await graphApi.getGraphData();
      setGraphData(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load graph:', err);
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, []);

  // Entity operations
  const handleCreateEntity = async (entity) => {
    try {
      await graphApi.createEntity(entity);
      await loadGraph();
    } catch (err) {
      alert(`Failed to create entity: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleUpdateEntity = async (entityId, updates) => {
    try {
      await graphApi.updateEntity(entityId, updates);
      await loadGraph();
      setSelectedNode(null);
    } catch (err) {
      alert(`Failed to update entity: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleDeleteEntity = async (entityId) => {
    try {
      await graphApi.deleteEntity(entityId);
      await loadGraph();
      setSelectedNode(null);
    } catch (err) {
      alert(`Failed to delete entity: ${err.response?.data?.detail || err.message}`);
    }
  };

  // Relation operations
  const handleCreateRelation = async (relation) => {
    try {
      await graphApi.createRelation(relation);
      await loadGraph();
    } catch (err) {
      alert(`Failed to create relation: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleDeleteRelation = async (fromId, toId, relation) => {
    try {
      await graphApi.deleteRelation(fromId, toId, relation);
      await loadGraph();
      setSelectedEdge(null);
    } catch (err) {
      alert(`Failed to delete relation: ${err.response?.data?.detail || err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading knowledge graph...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <h1>⚠️ Error</h1>
        <p>{error}</p>
        {error.includes('Authentication') && (
          <p className="hint">
            Add your token to the URL: <code>?token=YOUR_API_KEY</code>
          </p>
        )}
        <button className="btn btn-primary" onClick={loadGraph}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="app">
      <Toolbar
        onCreateEntity={handleCreateEntity}
        onCreateRelation={handleCreateRelation}
        onRefresh={loadGraph}
        nodes={graphData?.nodes || []}
        onLayoutChange={setLayout}
        onFilterChange={setFilters}
      />

      <div className="main-content">
        <div className="graph-container">
          <GraphCanvas
            graphData={graphData}
            onNodeClick={(node) => {
              setSelectedNode(node);
              setSelectedEdge(null);
            }}
            onEdgeClick={(edge) => {
              setSelectedEdge(edge);
              setSelectedNode(null);
            }}
            layout={layout}
            filters={filters}
          />
        </div>

        <div className="inspector-container">
          <InspectorPanel
            selectedNode={selectedNode}
            selectedEdge={selectedEdge}
            onUpdate={handleUpdateEntity}
            onDelete={(arg1, arg2, arg3) => {
              // Handle both entity and relation deletions
              if (arg2 === undefined) {
                // Entity deletion
                handleDeleteEntity(arg1);
              } else {
                // Relation deletion
                handleDeleteRelation(arg1, arg2, arg3);
              }
            }}
            onClose={() => {
              setSelectedNode(null);
              setSelectedEdge(null);
            }}
          />
        </div>
      </div>
    </div>
  );
}

export default App;
