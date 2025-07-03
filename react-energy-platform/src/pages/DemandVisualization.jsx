import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

// Reusing UI helper components (consider moving to a common directory if not already)
const Section = ({ title, children, style }) => (
  <section style={{ marginBottom: '25px', padding: '20px', border: '1px solid #e0e0e0', borderRadius: '8px', backgroundColor: '#f9f9f9', boxShadow: '0 2px 4px rgba(0,0,0,0.05)', ...style }}>
    <h3 style={{ marginTop: 0, borderBottom: '2px solid #007bff', paddingBottom: '10px', color: '#0056b3' }}>{title}</h3>
    {children}
  </section>
);
const PreFormatted = ({ data, style }) => <pre style={{ backgroundColor: '#e9ecef', padding: '15px', borderRadius: '5px', overflowX: 'auto', border: '1px solid #ced4da', fontSize: '0.85em', ...style }}>{JSON.stringify(data, null, 2)}</pre>;
const FormRow = ({ label, children, style }) => <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', gap: '10px', ...style }}><label style={{ minWidth: '180px', fontWeight: '500', color: '#495057', textAlign: 'right', paddingRight: '10px' }}>{label}:</label><div style={{flexGrow: 1}}>{children}</div></div>;
const Select = (props) => <select {...props} style={{ padding: '10px', border: '1px solid #ced4da', borderRadius: '4px', width: '100%', boxSizing: 'border-box', ...props.style }} />;
const Input = (props) => <input {...props} style={{ padding: '10px', border: '1px solid #ced4da', borderRadius: '4px', width: '100%', boxSizing: 'border-box', ...props.style }} />;
const Button = ({ children, onClick, type = "button", disabled = false, variant = "primary", style, title }) => <button title={title} type={type} onClick={onClick} disabled={disabled} style={{ padding: '10px 18px', cursor: disabled ? 'not-allowed' : 'pointer', border: 'none', borderRadius: '5px', fontWeight: 'bold', color: 'white', backgroundColor: disabled ? '#adb5bd' : (variant === 'danger' ? '#dc3545' : (variant === 'secondary' ? '#6c757d' : '#007bff')), opacity: disabled ? 0.7 : 1, minWidth: '100px', ...style }}>{children}</button>;
const AlertMessage = ({ message, type = "info" }) => { if (!message) return null; const s = {padding: '12px', margin: '15px 0', borderRadius: '5px', border: '1px solid transparent', color: type === 'error' ? '#721c24' : (type === 'success' ? '#155724' : '#0c5460'), backgroundColor: type === 'error' ? '#f8d7da' : (type === 'success' ? '#d4edda' : '#d1ecf1'), borderColor: type === 'error' ? '#f5c6cb' : (type === 'success' ? '#c3e6cb' : '#bee5eb')}; return <div style={s}>{message}</div>;};

const ModelSelectionEditor = ({ scenarioData, modelSelectionConfig, setModelSelectionConfig, onSave, isLoading, errorMsg }) => {
    if (!scenarioData || !scenarioData.sectors_data || !modelSelectionConfig) return <p>Load scenario data to configure model selection.</p>;

    const handleModelChange = (sectorName, selectedModel) => {
        setModelSelectionConfig(prev => ({ ...prev, [sectorName]: selectedModel }));
    };

    return (
        <div>
            <p>Select the desired forecasting model for each sector. This selection will be used when generating consolidated results.</p>
            {Object.entries(scenarioData.sectors_data).map(([sectorName, sectorInfo]) => (
                <FormRow key={sectorName} label={sectorName}>
                    <Select
                        value={modelSelectionConfig[sectorName] || ''}
                        onChange={(e) => handleModelChange(sectorName, e.target.value)}
                    >
                        <option value="">-- Select Model --</option>
                        {sectorInfo.models_available?.map(model => (
                            <option key={model} value={model}>{model}</option>
                        ))}
                    </Select>
                </FormRow>
            ))}
            <Button onClick={onSave} disabled={isLoading} style={{marginTop: '15px'}}>
                {isLoading ? "Saving..." : "Save Model Selection"}
            </Button>
            <AlertMessage message={errorMsg} type="error" />
        </div>
    );
};

// (Further UI enhancements for T&D Losses, Consolidated Results display, etc., would follow similar patterns)

const DemandVisualization = () => {
  const [projectName, setProjectName] = useState("Default_Project"); // Hardcoded
  const [availableScenarios, setAvailableScenarios] = useState([]);
  const [selectedScenarioName, setSelectedScenarioName] = useState('');

  const [scenarioData, setScenarioData] = useState(null); // ScenarioOutput type from service
  const [modelSelectionConfig, setModelSelectionConfig] = useState({}); // { sector: model }
  const [editableModelSelection, setEditableModelSelection] = useState({});

  const [tdLossesConfig, setTdLossesConfig] = useState([]); // List of {year, loss_percentage}
  const [editableTdLosses, setEditableTdLosses] = useState(''); // For JSON text area

  const [consolidatedData, setConsolidatedData] = useState(null);
  const [analysisSummary, setAnalysisSummary] = useState(null);
  const [validationStatus, setValidationStatus] = useState(null);

  const [loadingStates, setLoadingStates] = useState({ /* ... same as before ... */ });
  const [errorMessages, setErrorMessages] = useState({ /* ... same as before ... */ });
  const [actionMessage, setActionMessage] = useState({ text: '', type: 'info' });

  const updateLoading = (key, value) => setLoadingStates(prev => ({ ...prev, [key]: value }));
  const updateError = (key, value) => setErrorMessages(prev => ({ ...prev, [key]: value, general: value && key !== 'general' ? prev.general : value })); // Set specific and general error
  const clearError = (key) => { updateError(key, null); updateError('general', null); }; // Clear specific and general

  const showActionMessage = (text, type = 'info') => {
    setActionMessage({text, type});
    setTimeout(() => setActionMessage({text:'', type:'info'}), 5000); // Auto-clear after 5s
  };


  const fetchScenarios = useCallback(async () => { /* ... same as before ... */ }, [projectName]);
  useEffect(() => { fetchScenarios(); }, [fetchScenarios]);

  useEffect(() => {
    if (!selectedScenarioName || !projectName) { /* ... reset states ... */ return; }
    const fetchScenarioDetails = async () => {
      clearError('general');
      // Fetch Scenario Data
      updateLoading('scenarioDetails', true); updateError('scenarioDetails', null);
      try {
        const dataRes = await api.getDemandScenarioData(projectName, selectedScenarioName);
        setScenarioData(dataRes.data);
      } catch (err) { updateError('scenarioDetails', err.response?.data?.detail || err.message); }
      finally { updateLoading('scenarioDetails', false); }

      // Fetch Model Selection
      updateLoading('modelConfig', true); updateError('modelConfig', null);
      try {
        const modelRes = await api.getModelSelectionConfig(projectName, selectedScenarioName);
        setModelSelectionConfig(modelRes.data.model_selection || {});
        setEditableModelSelection(modelRes.data.model_selection || {}); // Initialize editable copy
      } catch (err) { updateError('modelConfig', err.response?.data?.detail || err.message); setModelSelectionConfig({}); setEditableModelSelection({});}
      finally { updateLoading('modelConfig', false); }

      // Fetch T&D Losses
      updateLoading('tdConfig', true); updateError('tdConfig', null);
      try {
        const tdRes = await api.getTdLossesConfig(projectName, selectedScenarioName);
        setTdLossesConfig(tdRes.data.td_losses || []);
        setEditableTdLosses(JSON.stringify(tdRes.data.td_losses || [], null, 2)); // For textarea
      } catch (err) { updateError('tdConfig', err.response?.data?.detail || err.message); setTdLossesConfig([]); setEditableTdLosses('[]');}
      finally { updateLoading('tdConfig', false); }

      // Fetch Validation Status
      updateLoading('validation', true); updateError('validation', null);
      try {
        const validationRes = await api.validateDemandScenario(projectName, selectedScenarioName);
        setValidationStatus(validationRes.data);
      } catch (err) { updateError('validation', err.response?.data?.detail || err.message); }
      finally { updateLoading('validation', false); }
    };
    fetchScenarioDetails();
  }, [projectName, selectedScenarioName]);

  const handleSaveModelSelection = async () => {
    if (!selectedScenarioName || !editableModelSelection) return;
    updateLoading('modelConfig', true); clearError('modelConfig');
    try {
      await api.saveModelSelectionConfig(projectName, selectedScenarioName, editableModelSelection);
      setModelSelectionConfig({...editableModelSelection}); // Update main state on success
      showActionMessage("Model selection saved successfully!", 'success');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Failed to save model selection";
      updateError('modelConfig', msg); showActionMessage(msg, 'error');
    } finally { updateLoading('modelConfig', false); }
  };

  const handleSaveTdLosses = async () => {
    if (!selectedScenarioName) return;
    updateLoading('tdConfig', true); clearError('tdConfig');
    let parsedTdLosses;
    try {
        parsedTdLosses = JSON.parse(editableTdLosses);
        if (!Array.isArray(parsedTdLosses)) throw new Error("T&D losses must be a JSON array.");
        // Add more validation for items if needed: [{year: YYYY, loss_percentage: X.X}]
    } catch (e) {
        updateError('tdConfig', `Invalid JSON for T&D Losses: ${e.message}`);
        updateLoading('tdConfig', false);
        return;
    }
    try {
        await api.saveTdLossesConfig(projectName, selectedScenarioName, parsedTdLosses);
        setTdLossesConfig([...parsedTdLosses]); // Update main state
        showActionMessage("T&D losses saved successfully!", 'success');
    } catch (err) {
        const msg = err.response?.data?.detail || err.message || "Failed to save T&D losses.";
        updateError('tdConfig', msg); showActionMessage(msg, 'error');
    } finally {
        updateLoading('tdConfig', false);
    }
  };

  const handleGenerateConsolidated = async () => {
    if (!selectedScenarioName || !modelSelectionConfig || !tdLossesConfig) {
        showActionMessage("Model selection and T&D losses must be configured first.", "error");
        return;
    }
    updateLoading('consolidated', true); clearError('consolidated'); setConsolidatedData(null);
    try {
        const payload = {
            model_selection: modelSelectionConfig,
            td_losses: tdLossesConfig,
            // filters: { unit: 'GWh' } // Example filter for display unit of results
        };
        const response = await api.generateConsolidatedResults(projectName, selectedScenarioName, payload);
        setConsolidatedData(response.data);
        showActionMessage("Consolidated results generated!", "success");
    } catch (err) {
        const msg = err.response?.data?.detail || err.message || "Failed to generate consolidated results.";
        updateError('consolidated', msg); showActionMessage(msg, 'error');
    } finally {
        updateLoading('consolidated', false);
    }
  };

  // Placeholder for handleFetchAnalysis, handleExport etc.

  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px'}}>
        Demand Visualization: Project <strong>{projectName}</strong>
      </h2>
      <AlertMessage message={actionMessage.text} type={actionMessage.type} />
      <AlertMessage message={errorMessages.general} type="error" />


      <Section title="Select Scenario">
        {loadingStates.scenarios && <p>Loading scenarios...</p>}
        <AlertMessage message={errorMessages.scenarios} type="error" />
        {availableScenarios.length > 0 ? (
          <FormRow label="Choose Scenario">
            <Select value={selectedScenarioName} onChange={e => setSelectedScenarioName(e.target.value)}>
              <option value="">-- Select a Scenario --</option>
              {availableScenarios.map(s => <option key={s.name} value={s.name}>{s.name} (Sectors: {s.sectors_count}, Files: {s.file_count})</option>)}
            </Select>
          </FormRow>
        ) : (
          !loadingStates.scenarios && <p>No scenarios found for this project.</p>
        )}
      </Section>

      {selectedScenarioName && (
        <>
          <Section title={`Data & Configurations for Scenario: ${selectedScenarioName}`}>
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px'}}>
              <div>
                <h4>Raw Scenario Data (Preview)</h4>
                {loadingStates.scenarioDetails && <p>Loading scenario data...</p>}
                <AlertMessage message={errorMessages.scenarioDetails} type="error" />
                {scenarioData && <PreFormatted data={{...scenarioData, sectors_data: "Truncated for preview..."}} />}
              </div>
              <div>
                <h4>Validation Status</h4>
                {loadingStates.validation && <p>Loading validation status...</p>}
                <AlertMessage message={errorMessages.validation} type="error" />
                {validationStatus && <PreFormatted data={validationStatus} />}
              </div>
            </div>
          </Section>

          <Section title="Model Selection Configuration">
            {loadingStates.modelConfig && <p>Loading model selection...</p>}
            <ModelSelectionEditor
                scenarioData={scenarioData}
                modelSelectionConfig={editableModelSelection}
                setModelSelectionConfig={setEditableModelSelection}
                onSave={handleSaveModelSelection}
                isLoading={loadingStates.modelConfig}
                errorMsg={errorMessages.modelConfig}
            />
          </Section>

          <Section title="T&D Losses Configuration">
            {loadingStates.tdConfig && <p>Loading T&D losses...</p>}
            <AlertMessage message={errorMessages.tdConfig} type="error" />
            {editableTdLosses !== null && ( // Check for null if it can be
              <div>
                <p>Define T&D losses as a JSON array of `{"{year": YYYY, "loss_percentage": X.X}` objects.</p>
                <textarea
                  rows="5"
                  style={{width: '100%', fontFamily: 'monospace', padding: '8px', border: '1px solid #ccc', boxSizing: 'border-box'}}
                  value={editableTdLosses}
                  onChange={(e) => setEditableTdLosses(e.target.value)}
                />
                <Button onClick={handleSaveTdLosses} disabled={loadingStates.tdConfig} style={{marginTop: '10px'}}>
                  {loadingStates.tdConfig ? "Saving..." : "Save T&D Losses"}
                </Button>
              </div>
            )}
          </Section>

          <Section title="Consolidated Results & Analysis">
            <Button onClick={handleGenerateConsolidated}
              disabled={loadingStates.consolidated || !modelSelectionConfig || Object.keys(modelSelectionConfig).length === 0 || !tdLossesConfig || tdLossesConfig.length === 0}
              title={(!modelSelectionConfig || Object.keys(modelSelectionConfig).length === 0 || !tdLossesConfig || tdLossesConfig.length === 0) ? "Configure Model Selection and T&D Losses first" : "Generate Consolidated Results"}
            >
              {loadingStates.consolidated ? "Generating..." : "Generate/View Consolidated Results"}
            </Button>
            <AlertMessage message={errorMessages.consolidated} type="error" />
            {consolidatedData && <PreFormatted data={consolidatedData} />}

            {consolidatedData && (
              <div style={{marginTop: '15px'}}>
                <Button disabled={true}>Get Analysis Summary (TODO)</Button>
                <AlertMessage message={errorMessages.analysis} type="error" />
                {analysisSummary && <PreFormatted data={analysisSummary} />}
              </div>
            )}
          </Section>

          <Section title="Export Data">
            <Button disabled={true} style={{marginRight: '10px'}}>Export Consolidated (TODO)</Button>
            <Button disabled={true}>Export Scenario Detail (TODO)</Button>
          </Section>
        </>
      )}
    </div>
  );
};

export default DemandVisualization;
