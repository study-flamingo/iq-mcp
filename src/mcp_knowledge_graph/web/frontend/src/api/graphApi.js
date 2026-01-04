import axios from 'axios';

// Get token from URL or localStorage
const getToken = () => {
  // Check URL params first
  const params = new URLSearchParams(window.location.search);
  const urlToken = params.get('token');

  if (urlToken) {
    localStorage.setItem('iq_auth_token', urlToken);
    // Clean URL
    window.history.replaceState({}, document.title, window.location.pathname);
    return urlToken;
  }

  // Fall back to localStorage
  return localStorage.getItem('iq_auth_token');
};

// Create axios instance with auth
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to all requests
api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('iq_auth_token');
      alert('Authentication failed. Please provide a valid token in the URL: ?token=YOUR_TOKEN');
    }
    return Promise.reject(error);
  }
);

export const graphApi = {
  // Get full graph data
  getGraphData: async () => {
    const response = await api.get('/graph/data');
    return response.data;
  },

  // Entity operations
  createEntity: async (entity) => {
    const response = await api.post('/graph/entity', entity);
    return response.data;
  },

  updateEntity: async (entityId, updates) => {
    const response = await api.patch(`/graph/entity/${entityId}`, updates);
    return response.data;
  },

  deleteEntity: async (entityId) => {
    const response = await api.delete(`/graph/entity/${entityId}`);
    return response.data;
  },

  // Relation operations
  createRelation: async (relation) => {
    const response = await api.post('/graph/relation', relation);
    return response.data;
  },

  deleteRelation: async (fromId, toId, relation) => {
    const response = await api.delete('/graph/relation', {
      params: { from_id: fromId, to_id: toId, relation }
    });
    return response.data;
  },

  // Observation operations
  addObservations: async (entityId, observations) => {
    const response = await api.post(`/graph/entity/${entityId}/observations`, observations);
    return response.data;
  },
};

export default api;
