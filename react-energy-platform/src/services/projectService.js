import api from './api'; // Central API client from api.js

/**
 * Service functions for interacting with the project management API endpoints.
 * Note: The base URL /api/v1 is configured in the api.js client.
 * Paths here are relative to that base, e.g., /projects/create maps to /api/v1/projects/create.
 */
const projectService = {
  /**
   * Creates a new project.
   * @param {{ projectName: string, projectLocation?: string }} projectData - Data for the new project.
   *        projectName is mandatory. projectLocation is optional.
   * @returns {Promise<AxiosResponse<any>>}
   */
  createProject: (projectData) => {
    // FastAPI endpoint: POST /api/v1/projects/create
    // Payload: { projectName: "name", projectLocation: "optional_location" }
    return api.post('/projects/create', projectData);
  },

  /**
   * Validates the structure of an existing project.
   * @param {string} projectPath - The absolute path to the project on the server.
   * @returns {Promise<AxiosResponse<any>>}
   */
  validateProject: (projectPath) => {
    // FastAPI endpoint: POST /api/v1/projects/validate
    // Payload: { projectPath: "/path/to/project" }
    return api.post('/projects/validate', { projectPath });
  },

  /**
   * Loads an existing project.
   * This also validates the project and adds it to the recent projects list on the backend.
   * @param {string} projectPath - The absolute path to the project on the server.
   * @returns {Promise<AxiosResponse<any>>}
   */
  loadProject: (projectPath) => {
    // FastAPI endpoint: POST /api/v1/projects/load
    // Payload: { projectPath: "/path/to/project" }
    return api.post('/projects/load', { projectPath });
  },

  /**
   * Fetches the list of recent projects.
   * @returns {Promise<AxiosResponse<any>>}
   */
  getRecentProjects: () => {
    // FastAPI endpoint: GET /api/v1/projects/recent
    return api.get('/projects/recent');
  },

  /**
   * Deletes a project from the recent projects list.
   * This does not delete the project from the disk.
   * @param {string} projectPath - The path of the project to remove from the recent list.
   * @returns {Promise<AxiosResponse<any>>}
   */
  deleteRecentProject: (projectPath) => {
    // FastAPI endpoint: POST /api/v1/projects/delete_recent
    // Payload: { projectPath: "/path/to/project/in/recent_list" }
    return api.post('/projects/delete_recent', { projectPath });
  },

  // Removed getProjectById as /load serves a similar purpose for existing projects.
  // Removed updateProject and deleteProject (disk deletion) as they are not
  // currently supported by the backend API as per the migration plan.
};

export default projectService;
