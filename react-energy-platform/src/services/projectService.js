import api from './api'; // Assuming a central api client

const projectService = {
  getProjects: () => {
    return api.get('/projects');
  },
  getProjectById: (id) => {
    return api.get(`/projects/${id}`);
  },
  createProject: (projectData) => {
    return api.post('/projects', projectData);
  },
  updateProject: (id, projectData) => {
    return api.put(`/projects/${id}`, projectData);
  },
  deleteProject: (id) => {
    return api.delete(`/projects/${id}`);
  },
};

export default projectService;
