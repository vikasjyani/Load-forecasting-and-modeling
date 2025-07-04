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
const Table = ({ headers, data, renderRow, caption }) => (
    <div style={{overflowX: 'auto'}}>
      <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9em'}}>
        {caption && <caption style={{ captionSide: 'top', textAlign: 'left', paddingBottom: '10px', fontWeight: 'bold', color: '#333' }}>{caption}</caption>}
        <thead>
          <tr>
            {headers.map(header => (
              <th key={header} style={{ border: '1px solid #ddd', padding: '10px 12px', textAlign: 'left', backgroundColor: '#007bff', color: 'white', textTransform: 'capitalize' }}>
                {header.replace(/_/g, ' ')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item, index) => renderRow(item, index))}
        </tbody>
      </table>
    </div>
  );

const PyPSAModeling = () => {
  const [projectName, setProjectName] = useState("Default_Project");
  const [availableScenarios, setAvailableScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState('');
  const [scenarioNetworkFiles, setScenarioNetworkFiles] = useState([]);
  const [selectedNetworkFile, setSelectedNetworkFile] = useState('');
  const [networkInfoDetail, setNetworkInfoDetail] = useState(null);

  const [runScenarioName, setRunScenarioName] = useState('');
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
  const [errorMessages, setErrorMessages] = useState({
    scenarios: null, networkFiles: null, networkInfo: null,
    run: null, status: null, extraction: null, systemStatus: null, general: null
  });

  const updateLoading = (key, value) => setLoadingStates(prev => ({ ...prev, [key]: value }));
  const updateError = (key, value) => setErrorMessages(prev => ({ ...prev, [key]: value, general: value && key !== 'general' ? prev.general : value }));
  const clearError = (key) => { updateError(key, null); updateError('general', null); };

  const pypsaExtractionFunctions = [
    { value: 'dispatch_data_payload_former', label: 'Dispatch Data (Generation, Load, Storage)' },
    { value: 'carrier_capacity_payload_former', label: 'Installed Capacity (by Carrier & Region)' },
    { value: 'new_capacity_additions_payload_former', label: 'New Capacity Additions' },
    { value: 'combined_metrics_extractor_wrapper', label: 'CUF & Curtailment Metrics' },
    { value: 'extract_api_storage_data_payload_former', label: 'Storage SoC & Stats' },
    { value: 'emissions_payload_former', label: 'CO2 Emissions' },
    { value: 'extract_api_prices_data_payload_former', label: 'Marginal Prices & Duration Curve' },
    { value: 'extract_api_network_flow_payload_former', label: 'Network Losses & Line Loading' },
  ];

  const fetchAvailableScenarios = useCallback(async () => {
    if (!projectName) return;
    updateLoading('scenarios', true); updateError('scenarios', null);
    try {
      const response = await api.listPyPSANetworks(projectName, null);
      setAvailableScenarios(response.data.networks || []);
      if (response.data.networks && response.data.networks.length > 0) {
        const firstScenario = response.data.networks[0].name;
        setSelectedScenario(firstScenario);
        setRunScenarioName(firstScenario);
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

   const fetchPyPSASystemStatus = useCallback(async () => {
    updateLoading('systemStatus', true); updateError('systemStatus', null);
    try {
      const response = await api.getPyPSASystemStatus();
      setPypsaSystemStatus(response.data);
    } catch (err) {
      updateError('systemStatus', err.response?.data?.detail || err.message || 'Failed to fetch PyPSA system status');
    } finally {
      updateLoading('systemStatus', false);
    }
  }, []);

  useEffect(() => {
    fetchAvailableScenarios();
    fetchPyPSASystemStatus();
  }, [fetchAvailableScenarios, fetchPyPSASystemStatus]);


  useEffect(() => {
    if (!selectedScenario || !projectName) {
      setScenarioNetworkFiles([]);
      setSelectedNetworkFile('');
      setNetworkInfoDetail(null);
      setExtractedPyPSAData(null);
      return;
    }
    const fetchFiles = async () => {
      updateLoading('networkFiles', true); updateError('networkFiles', null);
      try {
        const response = await api.listPyPSANetworks(projectName, selectedScenario);
        setScenarioNetworkFiles(response.data.networks || []);
        if (response.data.networks && response.data.networks.length > 0) {
          setSelectedNetworkFile(response.data.networks[0].name);
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

  useEffect(() => {
    if (!selectedNetworkFile || !selectedScenario || !projectName) {
      setNetworkInfoDetail(null);
      setExtractedPyPSAData(null);
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

  useEffect(() => {
    let intervalId;
    if (jobId && jobStatus?.status !== 'COMPLETED' && jobStatus?.status !== 'FAILED' && jobStatus?.status !== 'CANCELLED') {
      updateLoading('status', true);
      intervalId = setInterval(async () => {
        try {
          updateError('status', null);
          const response = await api.getPyPSAJobStatus(jobId);
          setJobStatus(response.data);
          setJobLog(response.data.log_summary || []);
          if (response.data.status === 'COMPLETED' || response.data.status === 'FAILED' || response.data.status === 'CANCELLED') {
            clearInterval(intervalId);
            updateLoading('status', false);
            fetchAvailableScenarios();
          }
        } catch (err) {
          console.error("Error fetching PyPSA job status:", err);
          const statusErrorMsg = err.response?.data?.detail || err.message || 'Failed to fetch job status.';
          updateError('status', statusErrorMsg);
          if (err.response?.status === 404) {
            clearInterval(intervalId);
            setJobStatus(prev => ({...prev, status: "NOT_FOUND", error_message: statusErrorMsg}));
            updateLoading('status', false);
          }
        }
      }, 5000);
    } else if (jobStatus?.status === 'COMPLETED' || jobStatus?.status === 'FAILED' || jobStatus?.status === 'CANCELLED') {
        updateLoading('status', false);
    }
    return () => clearInterval(intervalId);
  }, [jobId, jobStatus, fetchAvailableScenarios]);

  const handleRunSimulation = async (e) => {
    e.preventDefault();
    if (!runScenarioName) {
      updateError('run', "Please select or enter a scenario name to run.");
      return;
    }
    updateLoading('run', true);
    updateError('run', null);
    setJobId(null);
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
      scenario_name: runScenarioName,
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

  const handleExtractData = async (e) => {
    e.preventDefault();
    if (!selectedScenario || !selectedNetworkFile || !extractionFuncName) {
      updateError('extraction', "Scenario, Network File, and Extraction Function Name are required.");
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
      network_file_name: selectedNetworkFile,
      extraction_function_name: extractionFuncName,
      filters: parsedFilters,
      kwargs: {}
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

  const renderExtractedDataTables = (data) => {
    if (!data || !data.data) return <p>No data to display or data is not in expected format.</p>;

    const dataContent = data.data; // This is the dict returned by pau payload_formers

    return Object.entries(dataContent).map(([key, value]) => {
        if (Array.isArray(value) && value.length > 0 && typeof value[0] === 'object') {
            const headers = Object.keys(value[0]);
            return (
                <div key={key} style={{marginBottom: '15px'}}>
                    <h4 style={{textTransform: 'capitalize'}}>{key.replace(/_/g, ' ')}</h4>
                    {renderExtractedDataTable(value, key, headers)}
                </div>
            );
        } else if (typeof value === 'object' && value !== null && !Array.isArray(value)) { // Simple key-value object
            return (
                <div key={key} style={{marginBottom: '15px'}}>
                    <h4 style={{textTransform: 'capitalize'}}>{key.replace(/_/g, ' ')}</h4>
                    <PreFormatted data={value} />
                </div>
            );
        }
        // Add rendering for other data types if needed (e.g. simple lists, strings)
        return null;
    });
  };

  const renderExtractedDataTable = (dataArray, keyPrefix, headers) => {
    return (
      <Table
        headers={headers}
        data={dataArray}
        renderRow={(row, rowIndex) => (
          <tr key={`${keyPrefix}-${rowIndex}`} style={{backgroundColor: rowIndex % 2 === 0 ? 'white' : '#f0f8ff'}}>
            {headers.map(header => (
              <td key={`${keyPrefix}-${rowIndex}-${header}`} style={{border: '1px solid #ddd', padding: '8px', whiteSpace: 'nowrap', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis'}}>
                {typeof row[header] === 'object' ? JSON.stringify(row[header]) : String(row[header])}
              </td>
            ))}
          </tr>
        )}
      />
    );
  };

  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px', marginBottom: '20px'}}>
        PyPSA Power System Modeling: Project <strong>{projectName}</strong>
      </h2>
      <AlertMessage message={errorMessages.general} type="error" />

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
            <Select value={selectedScenario} onChange={e => {setSelectedScenario(e.target.value); setRunScenarioName(e.target.value);setSelectedNetworkFile(''); setNetworkInfoDetail(null); setExtractedPyPSAData(null);}}>
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
              <Select value={selectedNetworkFile} onChange={e => {setSelectedNetworkFile(e.target.value); setExtractedPyPSAData(null);}}>
                <option value="">-- Select Network File --</option>
                {scenarioNetworkFiles.map(nf => <option key={nf.name} value={nf.name}>{nf.name} ({nf.size_mb?.toFixed(2)}MB, Mod: {nf.last_modified_iso ? new Date(nf.last_modified_iso).toLocaleDateString() : 'N/A'})</option>)}
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
            <textarea value={uiOverrides} onChange={e => setUiOverrides(e.target.value)} rows={3} placeholder='e.g., {"solving": {"solver_options": {"threads": 4}}}' style={{padding: '8px', border: '1px solid #ced4da', borderRadius: '4px', flexGrow: 1, fontFamily: 'monospace', width: '100%', boxSizing: 'border-box'}}/>
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
        <Section title={`Extract Data from: ${selectedNetworkFile} (Scenario: ${selectedScenario})`}>
          <form onSubmit={handleExtractData} style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
            <FormRow label="Extraction Function Name">
              <Select value={extractionFuncName} onChange={e => setExtractionFuncName(e.target.value)}>
                {pypsaExtractionFunctions.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
              </Select>
            </FormRow>
            <FormRow label="Filters (JSON string)">
              <textarea value={extractionFilters} onChange={e => setExtractionFilters(e.target.value)} rows={3} placeholder='Default: {"resolution": "D"}. E.g., {"resolution": "H", "period": "2025"}' style={{padding: '8px', border: '1px solid #ced4da', borderRadius: '4px', flexGrow: 1, fontFamily: 'monospace', width: '100%', boxSizing: 'border-box'}}/>
            </FormRow>
            <Button type="submit" disabled={loadingStates.extraction}>
              {loadingStates.extraction ? 'Extracting...' : 'Extract Data'}
            </Button>
            <AlertMessage message={errorMessage.extraction} type="error" />
          </form>
          {extractedPyPSAData && (
            <div style={{marginTop: '20px'}}>
              <h4 style={{color:'#0056b3'}}>Extracted Data Preview:</h4>
              <AlertMessage message={extractedPyPSAData.metadata?.error} type="error" />
              {extractedPyPSAData.data && renderExtractedDataTables(extractedPyPSAData)}
              <h5 style={{marginTop:'15px'}}>Full Extraction Response:</h5>
              <PreFormatted data={extractedPyPSAData} />
            </div>
          )}
        </Section>
      )}
    </div>
  );
};

export default PyPSAModeling;
