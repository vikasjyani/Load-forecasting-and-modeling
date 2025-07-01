import api from './api';

const loadProfileService = {
  getLoadProfiles: () => {
    return api.get('/loadprofile');
  },
  getLoadProfileById: (id) => {
    return api.get(`/loadprofile/${id}`);
  },
  createLoadProfile: (profileData) => {
    // Assuming profileData might be form data for file upload
    // Adjust content type if it's a file upload
    return api.post('/loadprofile', profileData /*, { headers: { 'Content-Type': 'multipart/form-data' } }*/);
  },
  analyzeLoadProfile: (id, analysisConfig) => {
    return api.post(`/loadprofile_analysis/${id}`, analysisConfig);
  },
  // Add other load profile related API calls
};

export default loadProfileService;
