import { useState } from 'react';
import EntityForm from './EntityForm';
import RelationForm from './RelationForm';
import '../styles/Toolbar.css';

const Toolbar = ({ onCreateEntity, onCreateRelation, onRefresh, nodes, onLayoutChange, onFilterChange }) => {
  const [showEntityForm, setShowEntityForm] = useState(false);
  const [showRelationForm, setShowRelationForm] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentLayout, setCurrentLayout] = useState('cola');

  const handleLayoutChange = (e) => {
    const layout = e.target.value;
    setCurrentLayout(layout);
    onLayoutChange(layout);
  };

  const handleSearchChange = (e) => {
    const query = e.target.value;
    setSearchQuery(query);
    onFilterChange({ searchQuery: query });
  };

  return (
    <>
      <div className="toolbar">
        <div className="toolbar-section">
          <h1 className="toolbar-title">🔮 Knowledge Graph</h1>
        </div>

        <div className="toolbar-section toolbar-search">
          <input
            type="text"
            placeholder="Search nodes and observations..."
            value={searchQuery}
            onChange={handleSearchChange}
            className="search-input"
          />
        </div>

        <div className="toolbar-section toolbar-controls">
          <select value={currentLayout} onChange={handleLayoutChange} className="layout-select">
            <option value="cola">Force (Cola)</option>
            <option value="circle">Circle</option>
            <option value="grid">Grid</option>
            <option value="breadthfirst">Hierarchy</option>
            <option value="concentric">Concentric</option>
          </select>

          <button className="btn btn-sm" onClick={onRefresh}>
            🔄 Refresh
          </button>

          <button className="btn btn-sm btn-primary" onClick={() => setShowEntityForm(true)}>
            + Entity
          </button>

          <button className="btn btn-sm btn-primary" onClick={() => setShowRelationForm(true)}>
            + Relation
          </button>
        </div>
      </div>

      {/* Modals */}
      {showEntityForm && (
        <div className="modal-overlay" onClick={() => setShowEntityForm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create Entity</h2>
            <EntityForm
              onSave={(entity) => {
                onCreateEntity(entity);
                setShowEntityForm(false);
              }}
              onCancel={() => setShowEntityForm(false)}
            />
          </div>
        </div>
      )}

      {showRelationForm && (
        <div className="modal-overlay" onClick={() => setShowRelationForm(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>Create Relation</h2>
            <RelationForm
              nodes={nodes}
              onSave={(relation) => {
                onCreateRelation(relation);
                setShowRelationForm(false);
              }}
              onCancel={() => setShowRelationForm(false)}
            />
          </div>
        </div>
      )}
    </>
  );
};

export default Toolbar;
