// Example custom hook for project-related logic
// import { useState, useEffect, useCallback } from 'react';
// import projectService from '../services/projectService';
// import useApi from './useApi';

// const useProject = () => {
//   const { data: projects, loading, error, request: fetchProjects } = useApi(projectService.getProjects);
//   const { request: createProject } = useApi(projectService.createProject);

//   useEffect(() => {
//     fetchProjects();
//   }, [fetchProjects]);

//   const addProject = useCallback(async (projectData) => {
//     try {
//       await createProject(projectData);
//       fetchProjects(); // Refresh list after adding
//     } catch (e) {
//       // Error is handled by useApi, but can add specific logic here
//       console.error("Failed to add project:", e);
//     }
//   }, [createProject, fetchProjects]);

//   return { projects, loading, error, addProject, fetchProjects };
// };

// export default useProject;

// Placeholder content:
export default function useProject() {
  console.log("useProject hook placeholder");
  return {};
}
