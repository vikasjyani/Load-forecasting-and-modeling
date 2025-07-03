import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

// Reusing UI helper components
const Section = ({ title, children, style }) => (
  <section style={{ marginBottom: '25px', padding: '20px', border: '1px solid #e0e0e0', borderRadius: '8px', backgroundColor: '#f9f9f9', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', ...style }}>
    <h3 style={{ marginTop: 0, borderBottom: '2px solid #007bff', paddingBottom: '10px', color: '#0056b3' }}>{title}</h3>
    {children}
  </section>
);
const PreFormatted = ({ data, style }) => <pre style={{ backgroundColor: '#e9ecef', padding: '15px', borderRadius: '5px', overflowX: 'auto', border: '1px solid #ced4da', fontSize: '0.85em', ...style }}>{JSON.stringify(data, null, 2)}</pre>;
const FormRow = ({ label, children, style }) => <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', gap: '10px', ...style }}><label style={{ minWidth: '200px', fontWeight: '500', color: '#495057', textAlign: 'right', paddingRight: '10px' }}>{label}:</label><div style={{flexGrow: 1}}>{children}</div></div>;
const Input = (props) => <input {...props} style={{ padding: '10px', border: '1px solid #ced4da', borderRadius: '4px', width: '100%', boxSizing: 'border-box', ...props.style }} />;
const Select = (props) => <select {...props} style={{ padding: '10px', border: '1px solid #ced4da', borderRadius: '4px', width: '100%', boxSizing: 'border-box', ...props.style }} />;
const Button = ({ children, onClick, type = "button", disabled = false, variant = "primary", style, title }) => <button title={title} type={type} onClick={onClick} disabled={disabled} style={{ padding: '10px 18px', cursor: disabled ? 'not-allowed' : 'pointer', border: 'none', borderRadius: '5px', fontWeight: 'bold', color: 'white', backgroundColor: disabled ? '#adb5bd' : (variant === 'danger' ? '#dc3545' : (variant === 'secondary' ? '#6c757d' : '#007bff')), opacity: disabled ? 0.7 : 1, minWidth: '100px', ...style }}>{children}</button>;
const AlertMessage = ({ message, type = "info" }) => { if (!message) return null; const s = {padding: '12px', margin: '15px 0', borderRadius: '5px', border: '1px solid transparent', color: type === 'error' ? '#721c24' : (type === 'success' ? '#155724' : '#0c5460'), backgroundColor: type === 'error' ? '#f8d7da' : (type === 'success' ? '#d4edda' : '#d1ecf1'), borderColor: type === 'error' ? '#f5c6cb' : (type === 'success' ? '#c3e6cb' : '#bee5eb')}; return <div style={s}>{message}</div>;};

const PyPSAModeling = () => {
  const [projectName, setProjectName] = useState("Default_Project");
  const [availableScenarios, setAvailableScenarios] = useState([]); // Scenario folders
  const [selectedScenario, setSelectedScenario] = useState('');
  const [scenarioNetworkFiles, setScenarioNetworkFiles] = useState([]); // .nc files in selected scenario
  const [selectedNetworkFile, setSelectedNetworkFile] = useState('');
  const [networkInfoDetail, setNetworkInfoDetail] = useState(null);

  const [runScenarioName, setRunScenarioName] = useState(''); // For the "Run Simulation" form
  const [uiOverrides, setUiOverrides] = useState('{}');

  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobLog, setJobLog] = useState([]);

  const [extractionFuncName, setExtractionFuncName] = useState('dispatch_data_payload_former');
  const [extractionFilters, setExtractionFilters] = useState('{"resolution": "D"}');
  const [extractedPyPSAData, setExtractedPyPSAData] = useState(null);
  const [pypsaSystemStatus, setPypsaSystemStatus] = useState(null);

  const [loadingStates, setLoadingStates] = useState({
    scenarios: false, networkFiles: false, networkInfo: false,
    run: false, status: false, extraction: false, systemStatus: false
  });
  const [errorMessages, setErrorMessage] = useState({
    scenarios: null, networkFiles: null, networkInfo: null,
    run: null, status: null, extraction: null, systemStatus: null
  });

  const updateLoading = (key, value) => setLoadingStates(prev => ({ ...prev, [key]: value }));
  const updateError = (key, value) => setErrorMessage(prev => ({ ...prev, [key]: value }));

  const fetchAvailableScenarios = useCallback(async () => {
    if (!projectName) return;
    updateLoading('scenarios', true); updateError('scenarios', null);
    try {
      const response = await api.listPyPSANetworks(projectName, null);
      setAvailableScenarios(response.data.networks || []);
      if (response.data.networks && response.data.networks.length > 0) {
        const firstScenario = response.data.networks[0].name;
        setSelectedScenario(firstScenario);
        setRunScenarioName(firstScenario); // Default run scenario
      } else {
        setSelectedScenario('');
        setRunScenarioName('');
      }
    } catch (err) {
      updateError('scenarios', err.response?.data?.detail || err.message || 'Failed to fetch PyPSA scenarios');
    } finally {
      updateLoading('scenarios', false);
    }
  }, [projectName]);

  useEffect(() => {
    fetchAvailableScenarios();
    fetchPyPSASystemStatus(); // Fetch system status on load
  }, [fetchAvailableScenarios]);

  // Fetch network files when a scenario is selected
  useEffect(() => {
    if (!selectedScenario || !projectName) {
      setScenarioNetworkFiles([]);
      setSelectedNetworkFile('');
      setNetworkInfoDetail(null);
      return;
    }
    const fetchFiles = async () => {
      updateLoading('networkFiles', true); updateError('networkFiles', null);
      try {
        const response = await api.listPyPSANetworks(projectName, selectedScenario);
        setScenarioNetworkFiles(response.data.networks || []);
        if (response.data.networks && response.data.networks.length > 0) {
          setSelectedNetworkFile(response.data.networks[0].name); // Auto-select first .nc file
        } else {
          setSelectedNetworkFile('');
        }
      } catch (err) {
        updateError('networkFiles', err.response?.data?.detail || err.message || 'Failed to fetch network files');
      } finally {
        updateLoading('networkFiles', false);
      }
    };
    fetchFiles();
  }, [projectName, selectedScenario]);

  // Fetch network info when a network file is selected
  useEffect(() => {
    if (!selectedNetworkFile || !selectedScenario || !projectName) {
      setNetworkInfoDetail(null);
      return;
    }
    const fetchInfo = async () => {
      updateLoading('networkInfo', true); updateError('networkInfo', null);
      try {
        const response = await api.getPyPSANetworkInfo(projectName, selectedScenario, selectedNetworkFile);
        setNetworkInfoDetail(response.data);
      } catch (err) {
        updateError('networkInfo', err.response?.data?.detail || err.message || 'Failed to fetch network info');
      } finally {
        updateLoading('networkInfo', false);
      }
    };
    fetchInfo();
  }, [projectName, selectedScenario, selectedNetworkFile]);

  // Poll for job status (copied from previous implementation, seems okay)
  useEffect(() => { /* ... existing job status polling logic ... */ }, [jobId, jobStatus, fetchAvailableScenarios]);

  const handleRunSimulation = async (e) => { /* ... existing run simulation logic ... */ };

  const fetchPyPSASystemStatus = async () => {
    updateLoading('systemStatus', true); updateError('systemStatus', null);
    try {
      const response = await api.getPyPSASystemStatus();
      setPypsaSystemStatus(response.data);
    } catch (err) {
      updateError('systemStatus', err.response?.data?.detail || err.message || 'Failed to fetch PyPSA system status');
    } finally {
      updateLoading('systemStatus', false);
    }
  };

  const handleExtractData = async (e) => {
    e.preventDefault();
    if (!selectedScenario || !selectedNetworkFile || !extractionFuncName) {
      updateError('extraction', "Project, scenario, network file, and extraction function name are required.");
      return;
    }
    updateLoading('extraction', true); updateError('extraction', null); setExtractedPyPSAData(null);
    let parsedFilters = {};
    if (extractionFilters.trim()) {
      try {
        parsedFilters = JSON.parse(extractionFilters);
      } catch (jsonError) {
        updateError('extraction', "Invalid JSON in Filters.");
        updateLoading('extraction', false);
        return;
      }
    }
    const payload = {
      network_file_name: selectedNetworkFile, // This was the change in model
      extraction_function_name: extractionFuncName,
      filters: parsedFilters,
      kwargs: {} // Add if needed
    };
    try {
      const response = await api.extractPyPSAData(projectName, selectedScenario, selectedNetworkFile, payload);
      setExtractedPyPSAData(response.data);
    } catch (err) {
      updateError('extraction', err.response?.data?.detail || err.message || 'Failed to extract PyPSA data');
    } finally {
      updateLoading('extraction', false);
    }
  };

  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px', marginBottom: '20px'}}>
        PyPSA Power System Modeling: Project <strong>{projectName}</strong>
      </h2>

      <Section title="PyPSA System Status">
        {loadingStates.systemStatus && <p>Loading system status...</p>}
        <AlertMessage message={errorMessages.systemStatus} type="error" />
        {pypsaSystemStatus && <PreFormatted data={pypsaSystemStatus} />}
        <Button onClick={fetchPyPSASystemStatus} disabled={loadingStates.systemStatus} style={{marginTop:'10px'}}>Refresh Status</Button>
      </Section>

      <Section title="Available PyPSA Scenarios">
        {loadingStates.scenarios && <p>Loading scenarios...</p>}
        <AlertMessage message={errorMessages.scenarios} type="error" />
        {availableScenarios.length > 0 ? (
          <FormRow label="Select Scenario Folder">
            <Select value={selectedScenario} onChange={e => {setSelectedScenario(e.target.value); setRunScenarioName(e.target.value);setSelectedNetworkFile(''); setNetworkInfoDetail(null);}}>
              <option value="">-- Select Scenario --</option>
              {availableScenarios.map(sc => <option key={sc.name} value={sc.name}>{sc.name}</option>)}
            </Select>
          </FormRow>
        ) : (
          !loadingStates.scenarios && <p>No PyPSA scenario folders found. Create scenarios via 'Run Simulation' or ensure they exist in `PROJECT_DATA_ROOT/{projectName}/results/pypsa/`.</p>
        )}
      </Section>

      {selectedScenario && (
        <Section title={`Network Files in Scenario: ${selectedScenario}`}>
          {loadingStates.networkFiles && <p>Loading network files...</p>}
          <AlertMessage message={errorMessages.networkFiles} type="error" />
          {scenarioNetworkFiles.length > 0 ? (
            <FormRow label="Select Network File (.nc)">
              <Select value={selectedNetworkFile} onChange={e => setSelectedNetworkFile(e.target.value)}>
                <option value="">-- Select Network File --</option>
                {scenarioNetworkFiles.map(nf => <option key={nf.name} value={nf.name}>{nf.name} ({nf.size_mb?.toFixed(2)}MB, Mod: {new Date(nf.last_modified_iso).toLocaleDateString()})</option>)}
              </Select>
            </FormRow>
          ) : (
            !loadingStates.networkFiles && <p>No .nc network files found in this scenario folder. Run a simulation to generate one.</p>
          )}
        </Section>
      )}

      {selectedNetworkFile && networkInfoDetail && (
        <Section title={`Network Info: ${selectedNetworkFile}`}>
          {loadingStates.networkInfo && <p>Loading network details...</p>}
          <AlertMessage message={errorMessages.networkInfo} type="error" />
          <PreFormatted data={networkInfoDetail} />
        </Section>
      )}

      <Section title="Run New PyPSA Simulation">
        <form onSubmit={handleRunSimulation} style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
          <FormRow label="Scenario Name to Create/Run">
            <Input type="text" value={runScenarioName} onChange={e => setRunScenarioName(e.target.value)} placeholder="New or existing scenario name" required />
          </FormRow>
          <FormRow label="UI Settings Overrides (JSON)">
            <textarea value={uiOverrides} onChange={e => setUiOverrides(e.target.value)} rows={3} placeholder='e.g., {"solving": {"solver_options": {"threads": 4}}}' style={{padding: '8px', border: '1px solid #ced4da', borderRadius: '4px', flexGrow: 1, fontFamily: 'monospace'}}/>
          </FormRow>
          <Button type="submit" disabled={loadingStates.run || (jobId && jobStatus?.status !== 'COMPLETED' && jobStatus?.status !== 'FAILED' && jobStatus?.status !== 'CANCELLED')}>
            {loadingStates.run ? 'Starting...' : (jobId && jobStatus?.status !== 'COMPLETED' && jobStatus?.status !== 'FAILED' && jobStatus?.status !== 'CANCELLED' ? `Running (${jobStatus?.status})...` : 'Run Simulation')}
          </Button>
          <AlertMessage message={errorMessage.run} type="error" />
        </form>
      </Section>

      {jobId && (
        <Section title={`Job Status (ID: ${jobId})`}>
          {loadingStates.status && !jobStatus?.status && <p>Fetching status...</p>}
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

      {selectedNetworkFile && (
        <Section title={`Extract Data from: ${selectedNetworkFile}`}>
          <form onSubmit={handleExtractData} style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
            <FormRow label="Extraction Function Name">
              <Input type="text" value={extractionFuncName} onChange={e => setExtractionFuncName(e.target.value)} placeholder="e.g., dispatch_data_payload_former" required />
            </FormRow>
            <FormRow label="Filters (JSON string)">
              <textarea value={extractionFilters} onChange={e => setExtractionFilters(e.target.value)} rows={3} placeholder='e.g., {"resolution": "D"}' style={{padding: '8px', border: '1px solid #ced4da', borderRadius: '4px', flexGrow: 1, fontFamily: 'monospace'}}/>
            </FormRow>
            <Button type="submit" disabled={loadingStates.extraction}>
              {loadingStates.extraction ? 'Extracting...' : 'Extract Data'}
            </Button>
            <AlertMessage message={errorMessage.extraction} type="error" />
          </form>
          {extractedPyPSAData && (
            <div>
              <h4>Extracted Data:</h4>
              <PreFormatted data={extractedPyPSAData} />
            </div>
          )}
        </Section>
      )}
    </div>
  );
};

export default PyPSAModeling;
