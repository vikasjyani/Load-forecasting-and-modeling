// Central API service configuration
// import axios from 'axios';

// const apiClient = axios.create({
//   baseURL: process.env.REACT_APP_API_URL || '/api/v1', // Configurable API base URL
//   headers: {
//     'Content-Type': 'application/json',
//     // Add other common headers, e.g., for authorization
//   },
// });

// // Interceptors for request/response (e.g., token injection, error handling)
// apiClient.interceptors.request.use(config => {
//   // const token = localStorage.getItem('authToken');
//   // if (token) {
//   //   config.headers.Authorization = `Bearer ${token}`;
//   // }
//   return config;
// });

// apiClient.interceptors.response.use(
//   response => response,
//   error => {
//     // Handle global errors (e.g., 401, 500)
//     return Promise.reject(error);
//   }
// );

// export default apiClient;

// Placeholder content:
export default {
  get: (url, config) => Promise.resolve({ data: `Mock GET to ${url}`, config }),
  post: (url, data, config) => Promise.resolve({ data: `Mock POST to ${url} with ${JSON.stringify(data)}`, config }),
  put: (url, data, config) => Promise.resolve({ data: `Mock PUT to ${url} with ${JSON.stringify(data)}`, config }),
  delete: (url, config) => Promise.resolve({ data: `Mock DELETE to ${url}`, config }),
  // Add other methods like patch, head, options as needed
};
