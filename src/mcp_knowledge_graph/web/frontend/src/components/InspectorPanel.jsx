import { useState } from 'react';
import EntityForm from './EntityForm';
import RelationForm from './RelationForm';
import '../styles/InspectorPanel.css';

const InspectorPanel = ({ selectedNode, selectedEdge, onUpdate, onDelete, onClose }) => {
  const [isEditing, setIsEditing] = useState(false);

  if (!selectedNode && !selectedEdge) {
    return (
      <div className="inspector-panel">
        <div className="panel-empty">
          <h3>No Selection</h3>
          <p>Click on a node or edge to view details</p>
        </div>
      </div>
    );
  }

  if (selectedNode) {
    return (
      <div className="inspector-panel">
        <div className="panel-header">
          <h2>{selectedNode.icon} {selectedNode.name}</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        {!isEditing ? (
          <div className="panel-content">
            <div className="info-section">
              <label>Type:</label>
              <span className="badge">{selectedNode.entity_type}</span>
            </div>

            <div className="info-section">
              <label>ID:</label>
              <code className="entity-id">{selectedNode.id}</code>
            </div>

            {selectedNode.aliases && selectedNode.aliases.length > 0 && (
              <div className="info-section">
                <label>Aliases:</label>
                <div className="aliases">
                  {selectedNode.aliases.map((alias, idx) => (
                    <span key={idx} className="badge">{alias}</span>
                  ))}
                </div>
              </div>
            )}

            {selectedNode.observations && selectedNode.observations.length > 0 && (
              <div className="info-section">
                <label>Observations ({selectedNode.observations.length}):</label>
                <ul className="observations-list">
                  {selectedNode.observations.map((obs, idx) => (
                    <li key={idx} className="observation-item">
                      <div className="obs-content">{obs.content}</div>
                      <div className="obs-meta">
                        <span className={`durability ${obs.durability}`}>{obs.durability}</span>
                        <span className="timestamp">{new Date(obs.timestamp).toLocaleDateString()}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="panel-actions">
              <button className="btn btn-primary" onClick={() => setIsEditing(true)}>
                Edit
              </button>
              <button className="btn btn-danger" onClick={() => {
                if (confirm(`Delete entity "${selectedNode.name}"?`)) {
                  onDelete(selectedNode.id);
                }
              }}>
                Delete
              </button>
            </div>
          </div>
        ) : (
          <div className="panel-content">
            <EntityForm
              entity={selectedNode}
              onSave={(updates) => {
                onUpdate(selectedNode.id, updates);
                setIsEditing(false);
              }}
              onCancel={() => setIsEditing(false)}
            />
          </div>
        )}
      </div>
    );
  }

  if (selectedEdge) {
    return (
      <div className="inspector-panel">
        <div className="panel-header">
          <h2>Relation</h2>
          <button className="close-btn" onClick={onClose}>×</button>
        </div>

        <div className="panel-content">
          <div className="info-section">
            <label>From:</label>
            <code>{selectedEdge.source}</code>
          </div>

          <div className="info-section">
            <label>Relation:</label>
            <span className="relation-label">{selectedEdge.relation}</span>
          </div>

          <div className="info-section">
            <label>To:</label>
            <code>{selectedEdge.target}</code>
          </div>

          <div className="panel-actions">
            <button className="btn btn-danger" onClick={() => {
              if (confirm('Delete this relation?')) {
                onDelete(selectedEdge.source, selectedEdge.target, selectedEdge.relation);
              }
            }}>
              Delete Relation
            </button>
          </div>
        </div>
      </div>
    );
  }
};

export default InspectorPanel;
