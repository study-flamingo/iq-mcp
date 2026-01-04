import { useState } from 'react';
import '../styles/Forms.css';

const EntityForm = ({ entity = null, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: entity?.name || '',
    entity_type: entity?.entity_type || 'concept',
    icon: entity?.icon || '',
    aliases: entity?.aliases?.join(', ') || '',
    observations: entity?.observations || [],
  });

  const [newObservation, setNewObservation] = useState({
    content: '',
    durability: 'short-term',
  });

  const handleSubmit = (e) => {
    e.preventDefault();

    const updates = {
      name: formData.name,
      entity_type: formData.entity_type,
      icon: formData.icon || null,
      aliases: formData.aliases
        ? formData.aliases.split(',').map(a => a.trim()).filter(Boolean)
        : [],
      merge_aliases: true,
    };

    onSave(updates);
  };

  const addObservation = () => {
    if (!newObservation.content.trim()) return;

    setFormData({
      ...formData,
      observations: [...formData.observations, { ...newObservation }],
    });

    setNewObservation({ content: '', durability: 'short-term' });
  };

  return (
    <form className="entity-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label>Name *</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          required
          placeholder="Entity name"
        />
      </div>

      <div className="form-group">
        <label>Type *</label>
        <select
          value={formData.entity_type}
          onChange={(e) => setFormData({ ...formData, entity_type: e.target.value })}
        >
          <option value="person">Person</option>
          <option value="organization">Organization</option>
          <option value="event">Event</option>
          <option value="concept">Concept</option>
          <option value="project">Project</option>
          <option value="tool">Tool</option>
          <option value="place">Place</option>
          <option value="other">Other</option>
        </select>
      </div>

      <div className="form-group">
        <label>Icon (emoji)</label>
        <input
          type="text"
          value={formData.icon}
          onChange={(e) => setFormData({ ...formData, icon: e.target.value })}
          placeholder="👤"
          maxLength="2"
        />
      </div>

      <div className="form-group">
        <label>Aliases (comma-separated)</label>
        <input
          type="text"
          value={formData.aliases}
          onChange={(e) => setFormData({ ...formData, aliases: e.target.value })}
          placeholder="alias1, alias2, alias3"
        />
      </div>

      {!entity && (
        <div className="form-group observations-section">
          <label>Observations</label>

          {formData.observations.length > 0 && (
            <ul className="observations-preview">
              {formData.observations.map((obs, idx) => (
                <li key={idx}>
                  <span>{obs.content}</span>
                  <span className={`badge ${obs.durability}`}>{obs.durability}</span>
                </li>
              ))}
            </ul>
          )}

          <div className="observation-input">
            <input
              type="text"
              value={newObservation.content}
              onChange={(e) => setNewObservation({ ...newObservation, content: e.target.value })}
              placeholder="Add observation..."
            />
            <select
              value={newObservation.durability}
              onChange={(e) => setNewObservation({ ...newObservation, durability: e.target.value })}
            >
              <option value="temporary">Temporary</option>
              <option value="short-term">Short-term</option>
              <option value="long-term">Long-term</option>
              <option value="permanent">Permanent</option>
            </select>
            <button type="button" onClick={addObservation} className="btn btn-sm">
              Add
            </button>
          </div>
        </div>
      )}

      <div className="form-actions">
        <button type="submit" className="btn btn-primary">
          {entity ? 'Update' : 'Create'}
        </button>
        <button type="button" onClick={onCancel} className="btn">
          Cancel
        </button>
      </div>
    </form>
  );
};

export default EntityForm;
