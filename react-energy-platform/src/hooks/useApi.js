import { useState, useCallback } from 'react';
// import api from '../services/api'; // Assuming a central API service

const useApi = (apiFunction) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const request = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      // const result = await apiFunction(...args); // Using the passed API function
      // For placeholder, simulate API call
      await new Promise(resolve => setTimeout(resolve, 500));
      const result = { message: `Mock API response for ${apiFunction.name || 'unknown function'} with args: ${JSON.stringify(args)}`};
      setData(result);
      setLoading(false);
      return result;
    } catch (err) {
      setError(err);
      setLoading(false);
      throw err;
    }
  }, [apiFunction]);

  return { data, loading, error, request };
};

export default useApi;
