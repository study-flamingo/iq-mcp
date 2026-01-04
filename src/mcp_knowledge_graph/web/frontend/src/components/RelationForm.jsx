import { useState } from 'react';
import '../styles/Forms.css';

const RelationForm = ({ nodes, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    from_entity: '',
    to_entity: '',
    relation: '',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave(formData);
    setFormData({ from_entity: '', to_entity: '', relation: '' });
  };

  return (
    <form className="relation-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label>From Entity *</label>
        <select
          value={formData.from_entity}
          onChange={(e) => setFormData({ ...formData, from_entity: e.target.value })}
          required
        >
          <option value="">Select entity...</option>
          {nodes.map(node => (
            <option key={node.id} value={node.id}>
              {node.icon} {node.name}
            </option>
          ))}
        </select>
      </div>

      <div className="form-group">
        <label>Relation *</label>
        <input
          type="text"
          value={formData.relation}
          onChange={(e) => setFormData({ ...formData, relation: e.target.value })}
          required
          placeholder="e.g., works at, knows, manages"
        />
        <small>Use active voice (e.g., "works at", "created by")</small>
      </div>

      <div className="form-group">
        <label>To Entity *</label>
        <select
          value={formData.to_entity}
          onChange={(e) => setFormData({ ...formData, to_entity: e.target.value })}
          required
        >
          <option value="">Select entity...</option>
          {nodes.map(node => (
            <option key={node.id} value={node.id}>
              {node.icon} {node.name}
            </option>
          ))}
        </select>
      </div>

      <div className="form-actions">
        <button type="submit" className="btn btn-primary">
          Create Relation
        </button>
        <button type="button" onClick={onCancel} className="btn">
          Cancel
        </button>
      </div>
    </form>
  );
};

export default RelationForm;
