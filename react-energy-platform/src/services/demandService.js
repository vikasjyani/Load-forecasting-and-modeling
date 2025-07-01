import api from './api';

const demandService = {
  getDemandProjection: (config) => {
    // Assuming config might be query parameters for the projection
    return api.get('/demand_projection', { params: config });
  },
  getDemandVisualization: (type) => {
    return api.get(`/demand_visualization/${type}`); // Example, adjust as per API
  },
  // Add other demand-related API calls
};

export default demandService;
