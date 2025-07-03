// Central API service configuration
import axios from 'axios';

const apiClient = axios.create({
  // The Vite proxy is configured for '/api', and FastAPI uses '/api/v1'.
  // So, requests from React should go to '/api/v1/...'
  // Example: apiClient.get('/core/health') will request 'http://localhost:3000/api/v1/core/health'
  // Vite proxies '/api' part, so it becomes 'http://localhost:8000/api/v1/core/health' if FastAPI is on port 8000
  // However, FastAPI main router is already prefixed with /api/v1.
  // So, if FastAPI is at http://localhost:8000/api/v1, then baseURL for client should be this.
  // Vite proxy: target 'http://localhost:8000'. React calls '/api/v1/...'
  // Vite sends to 'http://localhost:8000/api/v1/...'
  // This means the baseURL for axios should be simply '/', and all calls must include the full path from /api/v1
  // OR, baseURL is '/api/v1' and calls are made to '/endpoint'.
  // Let's stick to baseURL being the prefix for the API version.
  baseURL: '/api/v1', // Vite handles proxying requests starting with /api
  headers: {
    'Content-Type': 'application/json',
    // Add other common headers, e.g., for authorization
  },
  timeout: 10000, // 10 seconds timeout
});

// Interceptors for request/response (e.g., token injection, error handling)
apiClient.interceptors.request.use(
  config => {
    // Example: const token = localStorage.getItem('authToken');
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`;
    // }
    console.debug('Starting API Request', config.method?.toUpperCase(), config.url, config.data);
    return config;
  },
  error => {
    console.error('API Request Error', error);
    return Promise.reject(error);
  }
);

apiClient.interceptors.response.use(
  response => {
    console.debug('API Response:', response.status, response.config.url, response.data);
    return response;
  },
  error => {
    console.error('API Response Error', error.response?.status, error.config?.url, error.response?.data);
    // Handle global errors (e.g., 401, 500) or specific error structures
    // Example: if (error.response && error.response.status === 401) {
    //   // Redirect to login or refresh token
    // }
    return Promise.reject(error); // It's important to reject the promise so calling code can handle it
  }
);

// --- API Service Functions ---

// Core endpoints
const getHealth = () => apiClient.get('/health'); // FastAPI root health is /health, not /core/health as per main.py
const getFastAPIRoot = () => apiClient.get('/'); // FastAPI root is /, not /core/ as per main.py
const getSystemInfo = () => apiClient.get('/core/system_info');
const getFeatureFlags = () => apiClient.get('/core/feature_flags');

// Demand Projection endpoints
const getProjectInputDataSummary = (projectName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/data_summary`);
const getSectorData = (projectName, sectorName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/sector_data/${encodeURIComponent(sectorName)}`);
const getIndependentVariables = (projectName, sectorName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/independent_variables/${encodeURIComponent(sectorName)}`);
const getCorrelationData = (projectName, sectorName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/correlation_data/${encodeURIComponent(sectorName)}`);
const getChartData = (projectName, sectorName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/chart_data/${encodeURIComponent(sectorName)}`); // Assuming this endpoint exists in FastAPI as per Flask
const runForecast = (projectName, payload) => apiClient.post(`/demand_projection/${encodeURIComponent(projectName)}/run_forecast`, payload);
const getForecastStatus = (jobId) => apiClient.get(`/demand_projection/forecast_status/${jobId}`);
const cancelForecast = (jobId) => apiClient.post(`/demand_projection/cancel_forecast/${jobId}`);
const getJobsSummary = () => apiClient.get('/demand_projection/jobs/summary');
const validateScenarioName = (projectName, scenarioName) => apiClient.post(`/demand_projection/${encodeURIComponent(projectName)}/validate_scenario_name`, { scenarioName });
const getScenarioConfiguration = (projectName, scenarioName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/configuration/${encodeURIComponent(scenarioName)}`);
const validateConfiguration = (projectName, payload) => apiClient.post(`/demand_projection/${encodeURIComponent(projectName)}/validate_configuration`, payload);


export default {
  getHealth,
  getFastAPIRoot,
  getSystemInfo,
  getFeatureFlags,

  // Demand Projection
  getProjectInputDataSummary,
  getSectorData,
  getIndependentVariables,
  getCorrelationData,
  getChartData,
  runForecast,
  getForecastStatus,
  cancelForecast,
  getJobsSummary,
  validateScenarioName,
  getScenarioConfiguration,
  validateConfiguration,

  // Load Profile endpoints
  getLoadProfileMainData: (projectName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/main_data`),
  getTemplateInfo: (projectName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/template_info`),
  getAvailableBaseYears: (projectName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/available_base_years`),
  getDemandScenarioInfo: (projectName, scenarioName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/demand_scenario/${encodeURIComponent(scenarioName)}`),
  previewBaseProfiles: (projectName, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/preview_base_profiles`, payload),
  generateBaseProfile: (projectName, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/generate_base_profile`, payload),
  generateStlProfile: (projectName, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/generate_stl_profile`, payload),
  listSavedLoadProfiles: (projectName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/profiles`),
  getLoadProfileData: (projectName, profileId) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/profiles/${encodeURIComponent(profileId)}`),
  // downloadLoadProfile: (projectName, profileId) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/profiles/${encodeURIComponent(profileId)}/download`, { responseType: 'blob' }), // Special handling for blob
  deleteLoadProfile: (projectName, profileId) => apiClient.delete(`/loadprofile/${encodeURIComponent(projectName)}/profiles/${encodeURIComponent(profileId)}`),
  uploadLoadProfileTemplate: (projectName, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/upload_template`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  },
  analyzeLoadProfile: (projectName, profileId, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/profiles/${encodeURIComponent(profileId)}/analysis`, payload),
  compareLoadProfiles: (projectName, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/compare_profiles`, payload),

  // You can also export apiClient directly if needed for custom requests elsewhere
  // apiClientInstance: apiClient
};
