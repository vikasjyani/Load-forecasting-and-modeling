import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api'; // Assuming api.js is correctly set up

// Reusing helper components from LoadProfile (consider moving to a common ui directory)
const Section = ({ title, children, style }) => (
  <section style={{ marginBottom: '25px', padding: '20px', border: '1px solid #e0e0e0', borderRadius: '8px', backgroundColor: '#f9f9f9', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', ...style }}>
    <h3 style={{ marginTop: 0, borderBottom: '2px solid #007bff', paddingBottom: '10px', color: '#0056b3' }}>{title}</h3>
    {children}
  </section>
);
const PreFormatted = ({ data, style }) => <pre style={{ backgroundColor: '#e9ecef', padding: '15px', borderRadius: '5px', overflowX: 'auto', border: '1px solid #ced4da', fontSize: '0.85em', ...style }}>{JSON.stringify(data, null, 2)}</pre>;
const FormRow = ({ label, children }) => <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', gap: '10px' }}><label style={{ minWidth: '180px', fontWeight: '500', color: '#495057' }}>{label}:</label>{children}</div>;
const Input = (props) => <input {...props} style={{ padding: '8px', border: '1px solid #ced4da', borderRadius: '4px', flexGrow: 1, ...props.style }} />;
const Button = ({ children, onClick, type = "button", disabled = false, variant = "primary", style }) => <button type={type} onClick={onClick} disabled={disabled} style={{ padding: '10px 18px', cursor: disabled ? 'not-allowed' : 'pointer', border: 'none', borderRadius: '5px', fontWeight: 'bold', color: 'white', backgroundColor: disabled ? '#adb5bd' : (variant === 'danger' ? '#dc3545' : '#007bff'), opacity: disabled ? 0.7 : 1, minWidth: '100px', ...style }}>{children}</button>;
const AlertMessage = ({ message, type = "info" }) => { if (!message) return null; const s = {padding: '12px', margin: '15px 0', borderRadius: '5px', border: '1px solid transparent', color: type === 'error' ? '#721c24' : (type === 'success' ? '#155724' : '#0c5460'), backgroundColor: type === 'error' ? '#f8d7da' : (type === 'success' ? '#d4edda' : '#d1ecf1'), borderColor: type === 'error' ? '#f5c6cb' : (type === 'success' ? '#c3e6cb' : '#bee5eb')}; return <div style={s}>{message}</div>;};

const PyPSAModeling = () => {
  const [projectName, setProjectName] = useState("Default_Project"); // Hardcoded for now
  const [availableNetworks, setAvailableNetworks] = useState([]); // Can be scenarios or .nc files
  const [scenarioToRun, setScenarioToRun] = useState('');
  const [uiOverrides, setUiOverrides] = useState(''); // JSON string for ui_settings_overrides

  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobLog, setJobLog] = useState([]);

  const [loadingState, setLoadingState] = useState({ networks: false, run: false, status: false });
  const [errorMessage, setErrorMessage] = useState({ networks: null, run: null, status: null });

  const updateLoading = (key, value) => setLoadingState(prev => ({ ...prev, [key]: value }));
  const updateError = (key, value) => setErrorMessage(prev => ({ ...prev, [key]: value }));

  const fetchAvailableNetworks = useCallback(async () => {
    if (!projectName) return;
    updateLoading('networks', true);
    updateError('networks', null);
    try {
      // First, list scenario folders. User might then select one to see .nc files, or run a scenario.
      const response = await api.listPyPSANetworks(projectName, null); // Passing null for scenarioName lists scenario folders
      setAvailableNetworks(response.data.networks || []);
      if (response.data.networks && response.data.networks.length > 0) {
        setScenarioToRun(response.data.networks[0].name); // Default to first scenario
      }
    } catch (err) {
      console.error("Error fetching PyPSA networks/scenarios:", err);
      updateError('networks', err.response?.data?.detail || err.message || 'Failed to fetch PyPSA networks/scenarios');
    } finally {
      updateLoading('networks', false);
    }
  }, [projectName]);

  useEffect(() => {
    fetchAvailableNetworks();
  }, [fetchAvailableNetworks]);

  // Poll for job status
  useEffect(() => {
    let intervalId;
    if (jobId && jobStatus?.status !== 'COMPLETED' && jobStatus?.status !== 'FAILED' && jobStatus?.status !== 'CANCELLED') { // Added CANCELLED
      updateLoading('status', true); // Ensure loading is true when polling starts
      intervalId = setInterval(async () => {
        try {
          updateError('status', null); // Clear previous status error
          const response = await api.getPyPSAJobStatus(jobId);
          setJobStatus(response.data);
          setJobLog(response.data.log_summary || []); // Use log_summary
          if (response.data.status === 'COMPLETED' || response.data.status === 'FAILED' || response.data.status === 'CANCELLED') {
            clearInterval(intervalId);
            updateLoading('status', false);
            fetchAvailableNetworks(); // Refresh network list in case new results are available
          }
        } catch (err) {
          console.error("Error fetching PyPSA job status:", err);
          const statusErrorMsg = err.response?.data?.detail || err.message || 'Failed to fetch job status.';
          updateError('status', statusErrorMsg);
          if (err.response?.status === 404) { // Job not found, stop polling
            clearInterval(intervalId);
            setJobStatus(prev => ({...prev, status: "NOT_FOUND", error_message: statusErrorMsg}));
            updateLoading('status', false);
          }
        }
      }, 5000); // Poll every 5 seconds
    } else if (jobStatus?.status === 'COMPLETED' || jobStatus?.status === 'FAILED' || jobStatus?.status === 'CANCELLED') {
        updateLoading('status', false); // Ensure loading is false if job is already in a final state
    }
    return () => clearInterval(intervalId); // Cleanup on unmount or if job ID/status changes
  }, [jobId, jobStatus, fetchAvailableNetworks]); // Added fetchAvailableNetworks to dependencies

  const handleRunSimulation = async (e) => {
    e.preventDefault();
    if (!scenarioToRun) {
      updateError('run', "Please select or enter a scenario name to run.");
      return;
    }
    updateLoading('run', true);
    updateError('run', null);
    setJobId(null); // Reset previous job ID
    setJobStatus(null);
    setJobLog([]);

    let parsedOverrides = {};
    if (uiOverrides.trim()) {
      try {
        parsedOverrides = JSON.parse(uiOverrides);
      } catch (jsonError) {
        updateError('run', "Invalid JSON in UI Settings Overrides. Please correct it.");
        updateLoading('run', false);
        return;
      }
    }

    const payload = {
      project_name: projectName,
      scenario_name: scenarioToRun,
      ui_settings_overrides: parsedOverrides,
    };

    try {
      const response = await api.runPyPSAJob(payload);
      setJobId(response.data.id);
      setJobStatus(response.data);
      setJobLog(response.data.log_summary || []);
    } catch (err) {
      console.error("Error running PyPSA simulation:", err);
      updateError('run', err.response?.data?.detail || err.message || 'Failed to start PyPSA simulation');
    } finally {
      updateLoading('run', false);
    }
  };

  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px'}}>
        PyPSA Power System Modeling: Project <strong>{projectName}</strong>
      </h2>

      <Section title="Available PyPSA Scenarios/Network Outputs">
        {loadingState.networks && <p>Loading available networks...</p>}
        <AlertMessage message={errorMessage.networks} type="error" />
        {availableNetworks.length > 0 ? (
          <ul style={{listStyleType: 'disc', paddingLeft: '20px'}}>
            {availableNetworks.map(net => (
              <li key={net.relative_path} style={{marginBottom: '5px'}}>
                <strong>{net.name}</strong>
                {net.relative_path !== net.name ? ` (Path: ${net.relative_path})` : ''}
                {net.size_mb && ` - Size: ${net.size_mb.toFixed(2)}MB`}
                {net.last_modified_iso && ` - Modified: ${new Date(net.last_modified_iso).toLocaleString()}`}
              </li>
            ))}
          </ul>
        ) : (
          !loadingState.networks && <p>No PyPSA scenarios or network results found for this project. Ensure PyPSA results are in the expected directory structure: `project_data_root/PROJECT_NAME/results/pypsa/SCENARIO_NAME/network_files.nc` or that scenario folders exist under `project_data_root/PROJECT_NAME/results/pypsa/`.</p>
        )}
      </Section>

      <Section title="Run PyPSA Simulation">
        <form onSubmit={handleRunSimulation} style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
          <FormRow label="Scenario Name to Run">
            <Input
              type="text"
              value={scenarioToRun}
              onChange={e => setScenarioToRun(e.target.value)}
              placeholder="Enter scenario name (directory name under project's pypsa results)"
              required
            />
          </FormRow>
          <FormRow label="UI Settings Overrides (JSON)">
            <textarea
              value={uiOverrides}
              onChange={e => setUiOverrides(e.target.value)}
              rows={3}
              placeholder='e.g., {"load_shedding": "True", "solver_options": {"crossover": "0"}}'
              style={{padding: '8px', border: '1px solid #ced4da', borderRadius: '4px', flexGrow: 1, fontFamily: 'monospace'}}
            />
          </FormRow>
          <Button type="submit" disabled={loadingState.run || (jobId && jobStatus?.status !== 'COMPLETED' && jobStatus?.status !== 'FAILED' && jobStatus?.status !== 'CANCELLED')}>
            {loadingState.run ? 'Starting...' : (jobId && jobStatus?.status !== 'COMPLETED' && jobStatus?.status !== 'FAILED' && jobStatus?.status !== 'CANCELLED' ? 'Running...' : 'Run Simulation')}
          </Button>
          <AlertMessage message={errorMessage.run} type="error" />
        </form>
      </Section>

      {jobId && (
        <Section title={`Job Status (ID: ${jobId})`}>
          {loadingState.status && <p>Fetching latest status...</p>}
          <AlertMessage message={errorMessage.status} type="error" />
          {jobStatus ? <PreFormatted data={jobStatus} /> : <p>No status data yet.</p>}

          <h4>Job Log Highlights:</h4>
          {jobLog.length > 0 ? (
            <ul style={{fontSize: '0.8em', maxHeight: '200px', overflowY: 'auto', backgroundColor: '#f8f9fa', padding: '10px', border: '1px solid #eee', borderRadius: '4px'}}>
              {jobLog.map((logEntry, index) => <li key={index} style={{borderBottom: '1px dotted #ccc', paddingBottom: '3px', marginBottom: '3px'}}>{logEntry}</li>)}
            </ul>
          ) : <p>No log entries yet.</p>}
        </Section>
      )}

      <Section title="PyPSA Results Visualization & Data Extraction">
        <p><em>(Components for selecting a processed network and extracting/visualizing specific data (e.g., dispatch, capacity, prices) will be added here once the backend data extraction services are fully implemented and available.)</em></p>
        {/* Example:
          <SelectNetwork onSelect={(networkFile) => setSelectedNetworkForAnalysis(networkFile)} availableNetworks={availableNetworks.filter(n => n.name.endsWith('.nc'))} />
          {selectedNetworkForAnalysis && <NetworkDataExtractor network={selectedNetworkForAnalysis} />}
        */}
      </Section>

    </div>
  );
};

export default PyPSAModeling;
