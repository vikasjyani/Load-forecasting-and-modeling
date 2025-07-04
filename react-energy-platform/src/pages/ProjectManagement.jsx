import React, { useState, useEffect, useCallback } from 'react';
import projectService from '../services/projectService'; // Corrected import path

const ProjectManagement = () => {
  const [recentProjects, setRecentProjects] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null); // For success/info messages

  // Form state for creating a new project
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectLocation, setNewProjectLocation] = useState(''); // Optional

  const fetchRecentProjects = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await projectService.getRecentProjects();
      setRecentProjects(response.data || []);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch recent projects.');
      setRecentProjects([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRecentProjects();
  }, [fetchRecentProjects]);

  const handleCreateProject = async (e) => {
    e.preventDefault();
    if (!newProjectName.trim()) {
      setError('Project name is required.');
      return;
    }
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const projectData = { projectName: newProjectName };
      if (newProjectLocation.trim()) {
        projectData.projectLocation = newProjectLocation;
      }
      const response = await projectService.createProject(projectData);
      setMessage(`Project "${response.data.project_name}" created successfully at ${response.data.project_path}`);
      setNewProjectName('');
      setNewProjectLocation('');
      fetchRecentProjects(); // Refresh the list
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to create project.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadProject = async (projectPath) => {
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      const response = await projectService.loadProject(projectPath);
      setMessage(`Project "${response.data.project_name}" loaded successfully. Path: ${response.data.project_path}`);
      // Here, you might want to update a global state or context with the loaded project info.
      // For now, just displaying a message.
      fetchRecentProjects(); // Refresh, as load adds to recent.
    } catch (err) {
      setError(err.response?.data?.detail || err.message || `Failed to load project: ${projectPath}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteRecentProject = async (projectPath) => {
    setIsLoading(true);
    setError(null);
    setMessage(null);
    try {
      await projectService.deleteRecentProject(projectPath);
      setMessage(`Project removed from recent list: ${projectPath}`);
      fetchRecentProjects(); // Refresh the list
    } catch (err) {
      setError(err.response?.data?.detail || err.message || `Failed to delete recent project: ${projectPath}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Basic styling (inline for simplicity, should be in CSS files)
  const styles = {
    container: { fontFamily: 'Arial, sans-serif', margin: '20px', padding: '20px', border: '1px solid #eee', borderRadius: '8px' },
    formGroup: { marginBottom: '15px' },
    label: { display: 'block', marginBottom: '5px', fontWeight: 'bold' },
    input: { width: '100%', padding: '8px', boxSizing: 'border-box', border: '1px solid #ccc', borderRadius: '4px' },
    button: { padding: '10px 15px', marginRight: '10px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
    buttonDanger: { backgroundColor: '#dc3545' },
    list: { listStyleType: 'none', padding: 0 },
    listItem: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', borderBottom: '1px solid #eee' },
    projectInfo: { flexGrow: 1 },
    actions: { whiteSpace: 'nowrap'},
    message: { padding: '10px', margin: '10px 0', borderRadius: '4px' },
    errorMessage: { backgroundColor: '#f8d7da', color: '#721c24', border: '1px solid #f5c6cb' },
    successMessage: { backgroundColor: '#d4edda', color: '#155724', border: '1px solid #c3e6cb' },
    loading: { textAlign: 'center', padding: '20px', fontSize: '1.2em' }
  };


  return (
    <div style={styles.container}>
      <h2>Project Management</h2>

      {message && <div style={{...styles.message, ...styles.successMessage}}>{message}</div>}
      {error && <div style={{...styles.message, ...styles.errorMessage}}>{error}</div>}

      <form onSubmit={handleCreateProject} style={{borderBottom: '1px solid #ccc', paddingBottom: '20px', marginBottom: '20px'}}>
        <h3>Create New Project</h3>
        <div style={styles.formGroup}>
          <label htmlFor="projectName" style={styles.label}>Project Name:</label>
          <input
            type="text"
            id="projectName"
            value={newProjectName}
            onChange={(e) => setNewProjectName(e.target.value)}
            required
            style={styles.input}
          />
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="projectLocation" style={styles.label}>Project Location (Optional, relative to data root or absolute):</label>
          <input
            type="text"
            id="projectLocation"
            value={newProjectLocation}
            onChange={(e) => setNewProjectLocation(e.target.value)}
            placeholder="e.g., 'my_studies' or '/mnt/shared/projects/kseb_data'"
            style={styles.input}
          />
        </div>
        <button type="submit" disabled={isLoading} style={styles.button}>
          {isLoading ? 'Creating...' : 'Create Project'}
        </button>
      </form>

      <h3>Recent Projects</h3>
      {isLoading && recentProjects.length === 0 && <p style={styles.loading}>Loading recent projects...</p>}
      {!isLoading && recentProjects.length === 0 && !error && <p>No recent projects found.</p>}

      {recentProjects.length > 0 && (
        <ul style={styles.list}>
          {recentProjects.map((project) => (
            <li key={project.path} style={styles.listItem}>
              <div style={styles.projectInfo}>
                <strong>{project.name}</strong>
                <br />
                <small>Path: {project.path}</small>
                <br />
                <small>Last Opened: {new Date(project.last_opened).toLocaleString()}</small>
              </div>
              <div style={styles.actions}>
                <button onClick={() => handleLoadProject(project.path)} disabled={isLoading} style={styles.button}>
                  {isLoading ? 'Loading...' : 'Load'}
                </button>
                <button
                  onClick={() => handleDeleteRecentProject(project.path)}
                  disabled={isLoading}
                  style={{...styles.button, ...styles.buttonDanger}}
                >
                  {isLoading ? 'Removing...' : 'Remove from Recent'}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ProjectManagement;
