import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

// Basic styled components for layout (can be moved to a separate file)
const Section = ({ title, children, style }) => (
  <section style={{ marginBottom: '20px', padding: '15px', border: '1px solid #eee', borderRadius: '8px', ...style }}>
    <h3>{title}</h3>
    {children}
  </section>
);

const PreFormatted = ({ data }) => <pre style={{backgroundColor: '#f5f5f5', padding: '10px', borderRadius: '4px', overflowX: 'auto'}}>{JSON.stringify(data, null, 2)}</pre>;

const styles = {
  container: { fontFamily: 'Arial, sans-serif', margin: '20px', padding: '20px', border: '1px solid #eee', borderRadius: '8px', backgroundColor: '#fff' },
  formGroup: { marginBottom: '15px' },
  label: { display: 'block', marginBottom: '5px', fontWeight: 'bold', fontSize: '0.9em' },
  input: { width: '100%', padding: '8px', boxSizing: 'border-box', border: '1px solid #ccc', borderRadius: '4px', marginBottom: '5px' },
  select: { width: '100%', padding: '8px', boxSizing: 'border-box', border: '1px solid #ccc', borderRadius: '4px', marginBottom: '5px' },
  button: { padding: '10px 15px', marginRight: '10px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' },
  buttonDanger: { backgroundColor: '#dc3545' },
  buttonWarning: { backgroundColor: '#ffc107', color: '#212529'},
  message: { padding: '10px', margin: '10px 0', borderRadius: '4px', fontSize: '0.9em' },
  errorMessage: { backgroundColor: '#f8d7da', color: '#721c24', border: '1px solid #f5c6cb' },
  successMessage: { backgroundColor: '#d4edda', color: '#155724', border: '1px solid #c3e6cb' },
  infoMessage: { backgroundColor: '#d1ecf1', color: '#0c5460', border: '1px solid #bee5eb' },
  loading: { textAlign: 'center', padding: '20px', fontSize: '1.2em', color: '#666' },
  checkboxGroup: { display: 'flex', alignItems: 'center', marginBottom: '10px'},
  checkboxInput: { marginRight: '8px', transform: 'scale(1.1)'},
  modelConfigSection: { borderLeft: '3px solid #007bff', paddingLeft: '15px', marginTop: '10px'}
};

const AVAILABLE_MODELS = ["SLR", "MLR", "WAM", "TimeSeries"]; // From constants typically

const DemandProjection = () => {
  // Project and Data Summary State
  const [projectName, setProjectName] = useState("Default_Project"); // TODO: Make this dynamic
  const [inputSummary, setInputSummary] = useState(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState(null); // General page errors

  // Sector Specific State
  const [selectedSector, setSelectedSector] = useState('');
  const [independentVarsInfo, setIndependentVarsInfo] = useState(null);
  const [loadingSectorInfo, setLoadingSectorInfo] = useState(false);

  // Forecast Configuration State
  const [scenarioName, setScenarioName] = useState(`Scenario_${new Date().toISOString().slice(0,10)}`);
  const [targetYear, setTargetYear] = useState(new Date().getFullYear() + 10);
  const [excludeCovidYears, setExcludeCovidYears] = useState(true);
  const [sectorConfigs, setSectorConfigs] = useState({}); // { sectorName: { models: [], independentVars: [], windowSize: 10 }}

  // Scenario/Config Validation State
  const [scenarioNameValidation, setScenarioNameValidation] = useState(null);
  const [configValidationResult, setConfigValidationResult] = useState(null);
  const [isValidatingConfig, setIsValidatingConfig] = useState(false);

  // Job Management State
  const [forecastJobId, setForecastJobId] = useState(null);
  const [forecastStatus, setForecastStatus] = useState(null);
  const [jobError, setJobError] = useState(null); // Errors specific to job polling/execution

  const fetchInputSummary = useCallback(async () => {
    if (!projectName) return;
    setLoadingSummary(true); setError(null);
    try {
      const response = await api.getProjectInputDataSummary(projectName);
      setInputSummary(response.data);
      if (response.data?.sectors_available?.length > 0) {
        const firstSector = response.data.sectors_available[0];
        setSelectedSector(firstSector);
        // Initialize sectorConfigs for all available sectors
        const initialSectorConfigs = {};
        response.data.sectors_available.forEach(sector => {
          initialSectorConfigs[sector] = { models: ['MLR'], independentVars: [], windowSize: 10, selectedForForecast: true };
        });
        setSectorConfigs(initialSectorConfigs);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to fetch input summary');
    } finally {
      setLoadingSummary(false);
    }
  }, [projectName]);

  useEffect(() => {
    fetchInputSummary();
  }, [fetchInputSummary]);

  useEffect(() => {
    if (!projectName || !selectedSector) {
      setIndependentVarsInfo(null);
      return;
    }
    const fetchSectorInfo = async () => {
      setLoadingSectorInfo(true);
      try {
        const indVarsRes = await api.getIndependentVariables(projectName, selectedSector);
        setIndependentVarsInfo(indVarsRes.data);
        // Update default independentVars for the selected sector if MLR is chosen
        setSectorConfigs(prev => ({
          ...prev,
          [selectedSector]: {
            ...prev[selectedSector],
            independentVars: indVarsRes.data?.suitable_variables?.slice(0, 2) || [] // Default to first 2 suitable
          }
        }));
      } catch (err) {
        setError(`Failed to fetch info for ${selectedSector}: ${err.response?.data?.detail || err.message}`);
      } finally {
        setLoadingSectorInfo(false);
      }
    };
    fetchSectorInfo();
  }, [projectName, selectedSector]);

  useEffect(() => { // Polling for forecast status
    let intervalId;
    if (forecastJobId && forecastStatus && forecastStatus.status !== 'COMPLETED' && forecastStatus.status !== 'FAILED' && forecastStatus.status !== 'CANCELLED') {
      intervalId = setInterval(async () => {
        try {
          setJobError(null);
          const response = await api.getForecastStatus(forecastJobId);
          setForecastStatus(response.data);
          if (['COMPLETED', 'FAILED', 'CANCELLED'].includes(response.data.status)) {
            clearInterval(intervalId);
          }
        } catch (err) {
          setJobError(`Error fetching job status: ${err.response?.data?.detail || err.message}`);
          if(err.response?.status === 404) clearInterval(intervalId); // Stop if job not found
        }
      }, 3000); // Poll every 3 seconds
    }
    return () => clearInterval(intervalId);
  }, [forecastJobId, forecastStatus]);

  const handleSectorConfigChange = (sector, field, value) => {
    setSectorConfigs(prev => ({
      ...prev,
      [sector]: { ...prev[sector], [field]: value }
    }));
  };

  const handleModelToggle = (sector, model) => {
    const currentModels = sectorConfigs[sector]?.models || [];
    const newModels = currentModels.includes(model)
      ? currentModels.filter(m => m !== model)
      : [...currentModels, model];
    handleSectorConfigChange(sector, 'models', newModels);
  };

  const handleIndVarToggle = (sector, indVar) => {
    const currentIndVars = sectorConfigs[sector]?.independentVars || [];
    const newIndVars = currentIndVars.includes(indVar)
      ? currentIndVars.filter(v => v !== indVar)
      : [...currentIndVars, indVar];
    handleSectorConfigChange(sector, 'independentVars', newIndVars);
  };

  const handleValidateScenarioName = async () => {
    if (!projectName || !scenarioName) return;
    try {
      const response = await api.validateScenarioName(projectName, scenarioName);
      setScenarioNameValidation(response.data);
    } catch (err) {
      setScenarioNameValidation({ error: `Failed to validate scenario name: ${err.response?.data?.detail || err.message}` });
    }
  };

  const handleValidateConfiguration = async () => {
    const activeSectorConfigs = Object.entries(sectorConfigs)
      .filter(([_,cfg]) => cfg.selectedForForecast)
      .reduce((acc, [sec, cfg]) => { acc[sec] = cfg; return acc; }, {});

    if (Object.keys(activeSectorConfigs).length === 0) {
      setConfigValidationResult({ errors: ["Please select at least one sector for forecasting."] });
      return;
    }
    const configPayload = {
      scenarioName, targetYear: parseInt(targetYear), excludeCovidYears,
      sectorConfigs: activeSectorConfigs,
      detailedConfiguration: {}, // Add if needed
    };
    setIsValidatingConfig(true); setConfigValidationResult(null);
    try {
      const response = await api.validateConfiguration(projectName, configPayload);
      setConfigValidationResult(response.data); // { is_valid: bool, message: str, errors?: [] }
    } catch (err) { // FastAPI returns 422 with detail if validation fails server-side (via HTTPException)
      setConfigValidationResult(err.response?.data?.detail || { errors: [`Failed to validate configuration: ${err.message}`] });
    } finally {
      setIsValidatingConfig(false);
    }
  };

  const handleRunForecast = async () => {
    const activeSectorConfigs = Object.entries(sectorConfigs)
      .filter(([_,cfg]) => cfg.selectedForForecast)
      .reduce((acc, [sec, cfg]) => { acc[sec] = cfg; return acc; }, {});

    if (Object.keys(activeSectorConfigs).length === 0) {
      alert("Please select at least one sector to forecast and configure its models.");
      return;
    }

    const finalConfig = {
      scenarioName,
      targetYear: parseInt(targetYear),
      excludeCovidYears,
      sectorConfigs: activeSectorConfigs,
      detailedConfiguration: {}, // Placeholder for global/advanced settings
    };

    setJobError(null); setForecastStatus(null); setForecastJobId(null);
    try {
      const response = await api.runForecast(projectName, finalConfig);
      setForecastJobId(response.data.job_id);
      setForecastStatus({ status: 'STARTING', message: 'Forecast job initiated...' });
    } catch (err) {
      setJobError(`Failed to start forecast: ${err.response?.data?.detail || err.message}`);
    }
  };

  const handleCancelForecast = async () => {
    if (!forecastJobId) return;
    try {
      await api.cancelForecast(forecastJobId);
      // Status will update via polling
    } catch (err) {
      setJobError(`Failed to cancel job: ${err.response?.data?.detail || err.message}`);
    }
  };

  if (loadingSummary) return <p style={styles.loading}>Loading project summary...</p>;
  if (error) return <div style={{...styles.message, ...styles.errorMessage}}><PreFormatted data={{ pageError: error }} /></div>;
  if (!inputSummary) return <p>No input data summary loaded. Ensure project '{projectName}' exists and has input_demand_file.xlsx.</p>;

  return (
    <div style={styles.container}>
      <h2>Demand Projection: {projectName}</h2>

      <Section title="1. Forecast Setup">
        <div style={styles.formGroup}>
          <label htmlFor="scenarioName" style={styles.label}>Scenario Name:</label>
          <input type="text" id="scenarioName" style={styles.input} value={scenarioName} onChange={e => setScenarioName(e.target.value)} onBlur={handleValidateScenarioName} />
          {scenarioNameValidation && <div style={scenarioNameValidation.error || scenarioNameValidation.already_exists ? styles.errorMessage : styles.infoMessage}><PreFormatted data={scenarioNameValidation} /></div>}
        </div>
        <div style={styles.formGroup}>
          <label htmlFor="targetYear" style={styles.label}>Target Year:</label>
          <input type="number" id="targetYear" style={styles.input} value={targetYear} onChange={e => setTargetYear(parseInt(e.target.value))} />
        </div>
        <div style={styles.checkboxGroup}>
          <input type="checkbox" id="excludeCovidYears" style={styles.checkboxInput} checked={excludeCovidYears} onChange={e => setExcludeCovidYears(e.target.checked)} />
          <label htmlFor="excludeCovidYears" style={styles.label}>Exclude COVID Years (2020, 2021)</label>
        </div>
      </Section>

      <Section title="2. Sector Configuration">
        <p style={{fontSize: '0.9em', color: '#555'}}>Configure models for each sector you want to include in the forecast.</p>
        {inputSummary.sectors_available?.map(sector => (
          <div key={sector} style={{border: '1px solid #ddd', padding: '10px', marginBottom: '10px', borderRadius: '4px'}}>
            <div style={styles.checkboxGroup}>
               <input type="checkbox" id={`select-sector-${sector}`} style={styles.checkboxInput}
                 checked={sectorConfigs[sector]?.selectedForForecast || false}
                 onChange={e => handleSectorConfigChange(sector, 'selectedForForecast', e.target.checked)}
               />
              <label htmlFor={`select-sector-${sector}`} style={{...styles.label, fontWeight: 'bold', fontSize: '1.1em'}}>{sector}</label>
            </div>

            {sectorConfigs[sector]?.selectedForForecast && (
              <div style={styles.modelConfigSection}>
                <div style={styles.formGroup}>
                  <label style={styles.label}>Models:</label>
                  {AVAILABLE_MODELS.map(model => (
                    <span key={model} style={{marginRight: '15px'}}>
                      <input type="checkbox" id={`${sector}-${model}`} style={styles.checkboxInput}
                        checked={sectorConfigs[sector]?.models?.includes(model) || false}
                        onChange={() => handleModelToggle(sector, model)} />
                      <label htmlFor={`${sector}-${model}`}>{model}</label>
                    </span>
                  ))}
                </div>

                {sectorConfigs[sector]?.models?.includes('MLR') && independentVarsInfo && independentVarsInfo.sector_name === sector && (
                  <div style={styles.formGroup}>
                    <label style={styles.label}>MLR Independent Variables for {sector}:</label>
                    {independentVarsInfo.suitable_variables?.map(indVar => (
                      <span key={indVar} style={{marginRight: '15px', display: 'block'}}>
                        <input type="checkbox" id={`${sector}-mlr-${indVar}`} style={styles.checkboxInput}
                          checked={sectorConfigs[sector]?.independentVars?.includes(indVar) || false}
                          onChange={() => handleIndVarToggle(sector, indVar)} />
                        <label htmlFor={`${sector}-mlr-${indVar}`}>{indVar}</label>
                      </span>
                    ))}
                    {(!independentVarsInfo.suitable_variables || independentVarsInfo.suitable_variables.length === 0) && <p style={{color: 'orange', fontSize: '0.9em'}}>No suitable independent variables found for MLR in {sector}.</p>}
                  </div>
                )}
                {sectorConfigs[sector]?.models?.includes('WAM') && (
                  <div style={styles.formGroup}>
                    <label htmlFor={`${sector}-wam-window`} style={styles.label}>WAM Window Size (Years) for {sector}:</label>
                    <input type="number" id={`${sector}-wam-window`} style={{...styles.input, width: '100px'}}
                      value={sectorConfigs[sector]?.windowSize || 10}
                      onChange={e => handleSectorConfigChange(sector, 'windowSize', parseInt(e.target.value))} />
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </Section>

      <Section title="3. Validate & Run Forecast">
        <button onClick={handleValidateConfiguration} disabled={isValidatingConfig} style={{...styles.button, ...styles.buttonWarning}}>
          {isValidatingConfig ? "Validating..." : "Validate Configuration"}
        </button>
        {configValidationResult && (
          <div style={configValidationResult.is_valid === false || configValidationResult.errors ? styles.errorMessage : styles.successMessage}>
            <PreFormatted data={configValidationResult} />
          </div>
        )}
        <button onClick={handleRunForecast}
          disabled={
            isValidatingConfig ||
            !configValidationResult || configValidationResult.is_valid === false ||
            (forecastJobId && forecastStatus && ['RUNNING', 'STARTING'].includes(forecastStatus.status))
          }
          style={styles.button}
        >
          Run Forecast
        </button>
      </Section>

      {forecastJobId && (
        <Section title="4. Forecast Job Status & Results">
          <p>Job ID: {forecastJobId}</p>
          {jobError && <div style={{...styles.message, ...styles.errorMessage}}><PreFormatted data={{ jobError }} /></div>}
          {forecastStatus && (
            <>
              <p>Status: <strong>{forecastStatus.status}</strong></p>
              <p>Message: {forecastStatus.current_message || forecastStatus.message}</p>
              <p>Progress: {forecastStatus.progress || 0}%</p>
              {forecastStatus.current_sector && <p>Current Sector: {forecastStatus.current_sector}</p>}
              {forecastStatus.elapsed_time_seconds !== undefined && <p>Elapsed Time: {forecastStatus.elapsed_time_seconds.toFixed(1)}s</p>}
              {forecastStatus.estimated_remaining_seconds !== undefined && <p>Est. Remaining: {forecastStatus.estimated_remaining_seconds.toFixed(1)}s</p>}

              {['RUNNING', 'STARTING'].includes(forecastStatus.status) && (
                <button onClick={handleCancelForecast} style={{...styles.button, ...styles.buttonDanger}}>Cancel Job</button>
              )}

              <h4>Full Status:</h4>
              <PreFormatted data={forecastStatus} />

              {forecastStatus.status === 'COMPLETED' && forecastStatus.result_summary && (
                <><h4>Result Summary:</h4> <PreFormatted data={forecastStatus.result_summary} /></>
              )}
              {forecastStatus.status === 'FAILED' && forecastStatus.error_message && (
                <><h4>Error Details:</h4> <PreFormatted data={{ error: forecastStatus.error_message, log: forecastStatus.detailed_log?.slice(-5) }} /></>
              )}
            </>
          )}
        </Section>
      )}

      <Section title="Data Explorer (Read-only)" style={{backgroundColor: '#fafafa'}}>
        <details>
          <summary>Input Data Summary (JSON)</summary>
          <PreFormatted data={inputSummary} />
        </details>
        {selectedSector && independentVarsInfo && (
          <details>
            <summary>Independent Variables for {selectedSector} (JSON)</summary>
            <PreFormatted data={independentVarsInfo} />
          </details>
        )}
      </Section>
    </div>
  );
};

export default DemandProjection;
