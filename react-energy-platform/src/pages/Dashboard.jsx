import React, { useState, useEffect } from 'react';
import api from '../services/api'; // Assuming api.js is correctly set up

const Dashboard = () => {
  const [healthData, setHealthData] = useState(null);
  const [systemInfo, setSystemInfo] = useState(null);
  const [featureFlags, setFeatureFlags] = useState(null);
  const [projectSummary, setProjectSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);

        // Fetch health status
        const healthResponse = await api.getHealth();
        setHealthData(healthResponse.data);

        // Fetch system info
        const systemInfoResponse = await api.getSystemInfo();
        setSystemInfo(systemInfoResponse.data);

        // Fetch feature flags
        const featureFlagsResponse = await api.getFeatureFlags();
        setFeatureFlags(featureFlagsResponse.data);

        // Example: Fetch project summary for a default/current project
        // Replace 'Default_Project' with actual logic to get current project name
        const currentProjectName = "Default_Project"; // Placeholder
        if (currentProjectName) {
            try {
                const summaryResponse = await api.getProjectInputDataSummary(currentProjectName);
                setProjectSummary(summaryResponse.data);
            } catch (projectError) {
                console.warn(`Could not load project summary for ${currentProjectName}:`, projectError.response?.data || projectError.message);
                setProjectSummary({ error: `Could not load project summary: ${projectError.response?.data?.detail || projectError.message}` });
            }
        }

      } catch (err) {
        console.error("Error fetching dashboard data:", err);
        setError(err.response?.data?.detail || err.message || 'Failed to fetch data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  if (loading) {
    return (
      <div>
        <h2>Dashboard</h2>
        <p>Loading dashboard data...</p>
      </div>
    );
  }

  return (
    <div>
      <h2>Dashboard</h2>
      <p>Welcome to the Energy Platform Dashboard.</p>

      {error && (
        <div style={{ color: 'red', border: '1px solid red', padding: '10px', margin: '10px 0' }}>
          <h3>Error Fetching Data</h3>
          <pre>{error}</pre>
        </div>
      )}

      <section>
        <h3>API Health Status</h3>
        {healthData ? <pre>{JSON.stringify(healthData, null, 2)}</pre> : <p>No health data.</p>}
      </section>

      <section>
        <h3>System Information</h3>
        {systemInfo ? <pre>{JSON.stringify(systemInfo, null, 2)}</pre> : <p>No system info.</p>}
      </section>

      <section>
        <h3>Feature Flags</h3>
        {featureFlags ? <pre>{JSON.stringify(featureFlags, null, 2)}</pre> : <p>No feature flag data.</p>}
      </section>

      <section>
        <h3>Project Input Data Summary (Default_Project)</h3>
        {projectSummary ? <pre>{JSON.stringify(projectSummary, null, 2)}</pre> : <p>No project summary loaded.</p>}
      </section>

      {/* Placeholder for more dashboard widgets and charts */}
    </div>
  );
};

export default Dashboard;
