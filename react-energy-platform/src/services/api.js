// Central API service configuration
import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

apiClient.interceptors.request.use(
  config => {
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
    return Promise.reject(error);
  }
);

// --- API Service Functions ---

// Core endpoints
const getHealth = () => apiClient.get('/health');
const getFastAPIRoot = () => apiClient.get('/');
const getSystemInfo = () => apiClient.get('/core/system_info');
const getFeatureFlags = () => apiClient.get('/core/feature_flags');

// Demand Projection endpoints
const getProjectInputDataSummary = (projectName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/data_summary`);
const getSectorData = (projectName, sectorName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/sector_data/${encodeURIComponent(sectorName)}`);
const getIndependentVariables = (projectName, sectorName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/independent_variables/${encodeURIComponent(sectorName)}`);
const getCorrelationData = (projectName, sectorName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/correlation_data/${encodeURIComponent(sectorName)}`);
const getChartData = (projectName, sectorName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/chart_data/${encodeURIComponent(sectorName)}`);
const runForecast = (projectName, payload) => apiClient.post(`/demand_projection/${encodeURIComponent(projectName)}/run_forecast`, payload);
const getForecastStatus = (jobId) => apiClient.get(`/demand_projection/forecast_status/${jobId}`);
const cancelForecast = (jobId) => apiClient.post(`/demand_projection/cancel_forecast/${jobId}`);
const getJobsSummary = () => apiClient.get('/demand_projection/jobs/summary');
const validateScenarioName = (projectName, scenarioName) => apiClient.post(`/demand_projection/${encodeURIComponent(projectName)}/validate_scenario_name`, { scenarioName });
const getScenarioConfiguration = (projectName, scenarioName) => apiClient.get(`/demand_projection/${encodeURIComponent(projectName)}/configuration/${encodeURIComponent(scenarioName)}`);
const validateConfiguration = (projectName, payload) => apiClient.post(`/demand_projection/${encodeURIComponent(projectName)}/validate_configuration`, payload);

// Load Profile endpoints
const getLoadProfileMainData = (projectName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/main_data`);
const getTemplateInfo = (projectName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/template_info`);
const getAvailableBaseYears = (projectName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/available_base_years`);
const getDemandScenarioInfo = (projectName, scenarioName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/demand_scenario/${encodeURIComponent(scenarioName)}`);
const previewBaseProfiles = (projectName, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/preview_base_profiles`, payload);
const generateBaseProfile = (projectName, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/generate_base_profile`, payload);
const generateStlProfile = (projectName, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/generate_stl_profile`, payload);
const listSavedLoadProfiles = (projectName) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/profiles`);
const getLoadProfileData = (projectName, profileId) => apiClient.get(`/loadprofile/${encodeURIComponent(projectName)}/profiles/${encodeURIComponent(profileId)}`);
const deleteLoadProfile = (projectName, profileId) => apiClient.delete(`/loadprofile/${encodeURIComponent(projectName)}/profiles/${encodeURIComponent(profileId)}`);
const uploadLoadProfileTemplate = (projectName, file) => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/upload_template`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
// analyzeLoadProfile and compareLoadProfiles might be better suited for a dedicated LoadProfileAnalysis service/section
// const analyzeLoadProfile = (projectName, profileId, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/profiles/${encodeURIComponent(profileId)}/analysis`, payload);
// const compareLoadProfiles = (projectName, payload) => apiClient.post(`/loadprofile/${encodeURIComponent(projectName)}/compare_profiles`, payload);

// PyPSA Endpoints
const runPyPSAJob = (payload) => apiClient.post('/pypsa/run_simulation', payload);
const getPyPSAJobStatus = (jobId) => apiClient.get(`/pypsa/job_status/${jobId}`);
const listPyPSANetworks = (projectName, scenarioName = null) => {
  let url = `/pypsa/${encodeURIComponent(projectName)}/networks`;
  if (scenarioName) {
    url += `?scenario_name=${encodeURIComponent(scenarioName)}`;
  }
  return apiClient.get(url);
};
const getPyPSANetworkInfo = (projectName, scenarioName, networkFileName) => apiClient.get(`/pypsa/${encodeURIComponent(projectName)}/scenario/${encodeURIComponent(scenarioName)}/network/${encodeURIComponent(networkFileName)}/info`);
const extractPyPSAData = (projectName, scenarioName, networkFileName, payload) => apiClient.post(`/pypsa/${encodeURIComponent(projectName)}/scenario/${encodeURIComponent(scenarioName)}/network/${encodeURIComponent(networkFileName)}/extract_data`, payload);
const comparePyPSANetworks = (projectName, payload) => apiClient.post(`/pypsa/${encodeURIComponent(projectName)}/compare_networks`, payload);
const getPyPSASystemStatus = () => apiClient.get('/pypsa/system_status');

// Admin Endpoints
const getAdminFeaturesConfig = (projectName = null) => {
  let url = '/admin/features';
  if (projectName) { url += `?project_name=${encodeURIComponent(projectName)}`; }
  return apiClient.get(url);
};
const updateAdminFeature = (featureId, payload, projectName = null) => {
  let url = `/admin/features/${encodeURIComponent(featureId)}`;
  if (projectName) { url += `?project_name=${encodeURIComponent(projectName)}`;}
  return apiClient.put(url, payload);
};
const bulkUpdateAdminFeatures = (payload) => apiClient.post('/admin/features/bulk_update', payload);
const triggerSystemCleanup = (payload) => apiClient.post('/admin/system/cleanup', payload);
const getAdminSystemInfo = () => apiClient.get('/admin/system/info');
const getAdminSystemHealth = () => apiClient.get('/admin/system/health');

// Color Management Endpoints
const getAllColors = () => apiClient.get('/colors/all');
const getCategoryColors = (category) => apiClient.get(`/colors/category/${encodeURIComponent(category)}`);
const getSectorColors = (sectors = null) => apiClient.get('/colors/sectors', { params: sectors ? { sectors } : {} });
const getModelColors = (models = null) => apiClient.get('/colors/models', { params: models ? { models } : {} });
const getCarrierColors = (carriers = null) => apiClient.get('/colors/carriers', { params: carriers ? { carriers } : {} });
const getChartColors = (count) => apiClient.get(`/colors/chart/${count}`);
const setColor = (payload) => apiClient.post('/colors/set', payload);
const setMultipleColors = (payload) => apiClient.post('/colors/set_multiple', payload);
const resetColors = (payload = null) => apiClient.post('/colors/reset', payload);
const exportColorsJS = () => apiClient.get('/colors/export/js');
const getColorPalette = (payload) => apiClient.post('/colors/palette', payload);
const getGradientColors = (gradientName) => apiClient.get(`/colors/gradient/${encodeURIComponent(gradientName)}`);
const getThemeColors = (themeName = 'light') => apiClient.get(`/colors/theme/${encodeURIComponent(themeName)}`);
const validateColorFormat = (payload) => apiClient.post('/colors/validate', payload);
const getColorStats = () => apiClient.get('/colors/stats');

// Demand Visualization Endpoints
const listDemandScenarios = (projectName) => apiClient.get(`/demand_visualization/${encodeURIComponent(projectName)}/scenarios`);
const getDemandScenarioData = (projectName, scenarioName, filters = {}) => apiClient.get(`/demand_visualization/${encodeURIComponent(projectName)}/scenario/${encodeURIComponent(scenarioName)}`, { params: filters });
const compareDemandScenarios = (projectName, scenario1Name, scenario2Name, filters = {}) => apiClient.get(`/demand_visualization/${encodeURIComponent(projectName)}/comparison`, { params: { scenario1: scenario1Name, scenario2: scenario2Name, ...filters } });
const getModelSelectionConfig = (projectName, scenarioName) => apiClient.get(`/demand_visualization/${encodeURIComponent(projectName)}/model_selection/${encodeURIComponent(scenarioName)}`);
const saveModelSelectionConfig = (projectName, scenarioName, modelSelection) => apiClient.post(`/demand_visualization/${encodeURIComponent(projectName)}/model_selection/${encodeURIComponent(scenarioName)}`, { model_selection: modelSelection });
const getTdLossesConfig = (projectName, scenarioName) => apiClient.get(`/demand_visualization/${encodeURIComponent(projectName)}/td_losses/${encodeURIComponent(scenarioName)}`);
const saveTdLossesConfig = (projectName, scenarioName, tdLosses) => apiClient.post(`/demand_visualization/${encodeURIComponent(projectName)}/td_losses/${encodeURIComponent(scenarioName)}`, { td_losses: tdLosses });
const generateConsolidatedResults = (projectName, scenarioName, payload) => apiClient.post(`/demand_visualization/${encodeURIComponent(projectName)}/consolidated_results/${encodeURIComponent(scenarioName)}`, payload);
const getAnalysisSummary = (projectName, scenarioName, filters = {}) => apiClient.get(`/demand_visualization/${encodeURIComponent(projectName)}/analysis_summary/${encodeURIComponent(scenarioName)}`, { params: filters });
const exportDemandData = async (projectName, scenarioName, dataType = 'consolidated', filters = {}) => {
  const response = await apiClient.get(`/demand_visualization/${encodeURIComponent(projectName)}/export/${encodeURIComponent(scenarioName)}`, {
    params: { data_type: dataType, ...filters },
    responseType: 'blob',
  });
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  const contentDisposition = response.headers['content-disposition'];
  let filename = `${scenarioName}_${dataType}_export.csv`;
  if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="?(.+)"?/i);
      if (filenameMatch && filenameMatch.length === 2)
          filename = filenameMatch[1];
  }
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
  return { success: true, filename: filename };
};
const validateDemandScenario = (projectName, scenarioName) => apiClient.get(`/demand_visualization/${encodeURIComponent(projectName)}/validate_configurations/${encodeURIComponent(scenarioName)}`);

// Load Profile Analysis Endpoints
const listAvailableProfilesForAnalysis = (projectName) => apiClient.get(`/loadprofile_analysis/${encodeURIComponent(projectName)}/available_profiles`);
const getStatisticalSummary = (projectName, profileId, unit = 'kW') => apiClient.get(`/loadprofile_analysis/${encodeURIComponent(projectName)}/profile/${encodeURIComponent(profileId)}/statistical_summary`, { params: { unit } });
const performLoadProfileAnalysis = (projectName, profileId, analysisType, params = null) => apiClient.post(`/loadprofile_analysis/${encodeURIComponent(projectName)}/profile/${encodeURIComponent(profileId)}/analyze/${encodeURIComponent(analysisType)}`, params);


export default {
  getHealth,
  getFastAPIRoot,
  getSystemInfo,
  getFeatureFlags,

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

  getLoadProfileMainData,
  getTemplateInfo,
  getAvailableBaseYears,
  getDemandScenarioInfo,
  previewBaseProfiles,
  generateBaseProfile,
  generateStlProfile,
  listSavedLoadProfiles,
  getLoadProfileData,
  deleteLoadProfile,
  uploadLoadProfileTemplate,
  // analyzeLoadProfile, // Moved to Load Profile Analysis section
  // compareLoadProfiles, // Moved to Load Profile Analysis section (or keep if distinct from DV compare)

  runPyPSAJob,
  getPyPSAJobStatus,
  listPyPSANetworks,
  getPyPSANetworkInfo,
  extractPyPSAData,
  comparePyPSANetworks,
  getPyPSASystemStatus,

  getAdminFeaturesConfig,
  updateAdminFeature,
  bulkUpdateAdminFeatures,
  triggerSystemCleanup,
  getAdminSystemInfo,
  getAdminSystemHealth,

  getAllColors,
  getCategoryColors,
  getSectorColors,
  getModelColors,
  getCarrierColors,
  getChartColors,
  setColor,
  setMultipleColors,
  resetColors,
  exportColorsJS,
  getColorPalette,
  getGradientColors,
  getThemeColors,
  validateColorFormat,
  getColorStats,

  listDemandScenarios,
  getDemandScenarioData,
  compareDemandScenarios,
  getModelSelectionConfig,
  saveModelSelectionConfig,
  getTdLossesConfig,
  saveTdLossesConfig,
  generateConsolidatedResults,
  getAnalysisSummary,
  exportDemandData,
  validateDemandScenario,

  listAvailableProfilesForAnalysis, // Added
  getStatisticalSummary, // Added
  performLoadProfileAnalysis, // Added
};
