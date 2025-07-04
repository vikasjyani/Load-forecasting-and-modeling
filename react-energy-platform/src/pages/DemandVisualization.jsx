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

// Reusing UI helper components (consider moving to a common ui directory if not already)
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

const TdLossesEditor = ({ tdLossesConfig, setTdLossesConfig, onSave, isLoading, errorMsg }) => {
    const [localLosses, setLocalLosses] = useState(tdLossesConfig || []);

    useEffect(() => { // Sync with prop changes
        setLocalLosses(tdLossesConfig || []);
    }, [tdLossesConfig]);

    const handleLossChange = (index, field, value) => {
        const updatedLosses = [...localLosses];
        updatedLosses[index] = { ...updatedLosses[index], [field]: field === 'year' ? parseInt(value) || '' : parseFloat(value) || '' };
        setLocalLosses(updatedLosses);
    };

    const addLossEntry = () => setLocalLosses([...localLosses, { year: '', loss_percentage: '' }]);
    const removeLossEntry = (index) => setLocalLosses(localLosses.filter((_, i) => i !== index));

    const handleSave = () => {
        // Validate entries before saving
        const validLosses = localLosses.filter(entry =>
            entry.year && typeof entry.year === 'number' &&
            entry.loss_percentage !== '' && typeof entry.loss_percentage === 'number' && !isNaN(entry.loss_percentage)
        );
        if (validLosses.length !== localLosses.length) {
            // Or set specific error message for the component
            alert("Please ensure all T&D loss entries have valid year and numeric percentage.");
            return;
        }
        setTdLossesConfig(validLosses); // Update parent state for saving
        onSave(validLosses); // Call parent save function
    };

    return (
        <div>
            <p>Define T&D losses as a percentage for different years. These will be interpolated.</p>
            {localLosses.map((entry, index) => (
                <FormRow key={index} label={`Entry ${index + 1}`} style={{borderBottom: '1px dashed #eee', paddingBottom: '10px'}}>
                    <Input type="number" placeholder="Year (e.g., 2025)" value={entry.year} onChange={e => handleLossChange(index, 'year', e.target.value)} style={{marginRight: '10px'}} />
                    <Input type="number" step="0.1" placeholder="Loss % (e.g., 5.5)" value={entry.loss_percentage} onChange={e => handleLossChange(index, 'loss_percentage', e.target.value)} style={{marginRight: '10px'}}/>
                    <Button onClick={() => removeLossEntry(index)} variant="danger" style={{padding: '5px 10px'}}>Remove</Button>
                </FormRow>
            ))}
            <Button onClick={addLossEntry} variant="secondary" style={{marginTop: '10px'}}>Add Loss Entry</Button>
            <Button onClick={handleSave} disabled={isLoading} style={{marginTop: '10px', marginLeft: '10px'}}>
                {isLoading ? "Saving..." : "Save T&D Losses"}
            </Button>
            <AlertMessage message={errorMsg} type="error" />
        </div>
    );
};


const DemandVisualization = () => {
  const [projectName, setProjectName] = useState("Default_Project");
  const [availableScenarios, setAvailableScenarios] = useState([]);
  const [selectedScenarioName, setSelectedScenarioName] = useState('');

  const [scenarioData, setScenarioData] = useState(null);
  const [modelSelectionConfig, setModelSelectionConfig] = useState({});
  // No separate editableModelSelection, ModelSelectionEditor will manage its internal draft if needed or call onSave with current data

  const [tdLossesConfig, setTdLossesConfig] = useState([]);
  // editableTdLosses removed, TdLossesEditor manages its internal draft

  const [consolidatedData, setConsolidatedData] = useState(null);
  const [analysisSummary, setAnalysisSummary] = useState(null);
  const [validationStatus, setValidationStatus] = useState(null);

  const [loadingStates, setLoadingStates] = useState({
    scenarios: false, scenarioDetails: false, modelConfigSave: false, tdConfigSave: false,
    consolidated: false, analysis: false, validation: false, export: false,
   });
  const [errorMessages, setErrorMessages] = useState({
    scenarios: null, scenarioDetails: null, modelConfig: null, tdConfig: null,
    consolidated: null, analysis: null, validation: null, export: null, general: null,
   });
  const [actionMessage, setActionMessage] = useState({ text: '', type: 'info' });

  const updateLoading = (key, value) => setLoadingStates(prev => ({ ...prev, [key]: value }));
  const updateError = (key, value) => setErrorMessages(prev => ({ ...prev, [key]: value, general: value && key !== 'general' ? prev.general : value }));
  const clearError = (key) => { updateError(key, null); updateError('general', null); };

  const showActionMessage = (text, type = 'info') => { /* ... same as before ... */ };
  const fetchScenarios = useCallback(async () => { /* ... same as before ... */ }, [projectName]);
  useEffect(() => { fetchScenarios(); }, [fetchScenarios]);

  useEffect(() => {
    if (!selectedScenarioName || !projectName) {
        setScenarioData(null); setModelSelectionConfig({}); setTdLossesConfig([]);
        setConsolidatedData(null); setAnalysisSummary(null); setValidationStatus(null);
        setErrorMessages({}); // Clear all errors
        return;
    }
    const fetchScenarioDetails = async () => {
      clearError('general');
      updateLoading('scenarioDetails', true); updateError('scenarioDetails', null);
      try {
        const dataRes = await api.getDemandScenarioData(projectName, selectedScenarioName);
        setScenarioData(dataRes.data);
      } catch (err) { updateError('scenarioDetails', err.response?.data?.detail || err.message); }
      finally { updateLoading('scenarioDetails', false); }

      updateLoading('modelConfigSave', true); updateError('modelConfig', null); // Use modelConfigSave for loading indicator
      try {
        const modelRes = await api.getModelSelectionConfig(projectName, selectedScenarioName);
        setModelSelectionConfig(modelRes.data.model_selection || {});
      } catch (err) { updateError('modelConfig', err.response?.data?.detail || err.message); setModelSelectionConfig({});}
      finally { updateLoading('modelConfigSave', false); }

      updateLoading('tdConfigSave', true); updateError('tdConfig', null); // Use tdConfigSave for loading indicator
      try {
        const tdRes = await api.getTdLossesConfig(projectName, selectedScenarioName);
        setTdLossesConfig(tdRes.data.td_losses || []);
      } catch (err) { updateError('tdConfig', err.response?.data?.detail || err.message); setTdLossesConfig([]);}
      finally { updateLoading('tdConfigSave', false); }

      updateLoading('validation', true); updateError('validation', null);
      try {
        const validationRes = await api.validateDemandScenario(projectName, selectedScenarioName);
        setValidationStatus(validationRes.data);
      } catch (err) { updateError('validation', err.response?.data?.detail || err.message); }
      finally { updateLoading('validation', false); }
    };
    fetchScenarioDetails();
  }, [projectName, selectedScenarioName]);

  const handleSaveModelSelection = async (currentEditableModelSelection) => { // Receives data from editor
    if (!selectedScenarioName || !currentEditableModelSelection) return;
    updateLoading('modelConfigSave', true); clearError('modelConfig');
    try {
      await api.saveModelSelectionConfig(projectName, selectedScenarioName, currentEditableModelSelection);
      setModelSelectionConfig({...currentEditableModelSelection});
      showActionMessage("Model selection saved successfully!", 'success');
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Failed to save model selection";
      updateError('modelConfig', msg); showActionMessage(msg, 'error');
    } finally { updateLoading('modelConfigSave', false); }
  };

  const handleSaveTdLosses = async (currentEditableTdLosses) => { // Receives data from editor
    if (!selectedScenarioName) return;
    updateLoading('tdConfigSave', true); clearError('tdConfig');
    try {
        // Validation for currentEditableTdLosses (array of {year, loss_percentage}) should be in TdLossesEditor or here
        await api.saveTdLossesConfig(projectName, selectedScenarioName, currentEditableTdLosses);
        setTdLossesConfig([...currentEditableTdLosses]);
        showActionMessage("T&D losses saved successfully!", 'success');
    } catch (err) {
        const msg = err.response?.data?.detail || err.message || "Failed to save T&D losses.";
        updateError('tdConfig', msg); showActionMessage(msg, 'error');
    } finally {
        updateLoading('tdConfigSave', false);
    }
  };

  const handleGenerateConsolidated = async () => { /* ... same as before ... */ };

  const handleFetchAnalysis = async () => {
    if (!selectedScenarioName) {
        showActionMessage("Please select a scenario first.", "error");
        return;
    }
    updateLoading('analysis', true); clearError('analysis'); setAnalysisSummary(null);
    try {
        // Assuming default filters for now, or add UI for filters
        const response = await api.getAnalysisSummary(projectName, selectedScenarioName, {});
        setAnalysisSummary(response.data);
        showActionMessage("Analysis summary fetched!", "success");
    } catch (err) {
        const msg = err.response?.data?.detail || err.message || "Failed to fetch analysis summary.";
        updateError('analysis', msg); showActionMessage(msg, 'error');
    } finally {
        updateLoading('analysis', false);
    }
  };

  const handleExport = async (dataType) => {
    if (!selectedScenarioName) {
        showActionMessage("Please select a scenario to export data.", "error");
        return;
    }
    updateLoading('export', true); clearError('export');
    try {
        await api.exportDemandData(projectName, selectedScenarioName, dataType, {});
        showActionMessage(`Export for ${dataType} started. Check your downloads.`, "success");
    } catch (err) {
        const msg = err.response?.data?.detail || err.message || `Failed to export ${dataType} data.`;
        updateError('export', msg); showActionMessage(msg, 'error');
    } finally {
        updateLoading('export', false);
    }
  };


  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px'}}>
        Demand Visualization: Project <strong>{projectName}</strong>
      </h2>
      <AlertMessage message={actionMessage.text} type={actionMessage.type} />
      <AlertMessage message={errorMessages.general} type="error" />

      <Section title="Select Scenario">
        {/* ... Scenario Selection UI ... */}
      </Section>

      {selectedScenarioName && (
        <>
          <Section title={`Data & Configurations for Scenario: ${selectedScenarioName}`}>
            {/* ... Scenario Data & Validation Display ... */}
          </Section>

          <Section title="Model Selection Configuration">
            <ModelSelectionEditor
                scenarioData={scenarioData}
                modelSelectionConfig={modelSelectionConfig} // Pass the main config
                setModelSelectionConfig={setModelSelectionConfig} // Allow editor to update draft or call save
                onSave={handleSaveModelSelection} // Editor calls this with its current state
                isLoading={loadingStates.modelConfigSave}
                errorMsg={errorMessages.modelConfig}
            />
          </Section>

          <Section title="T&D Losses Configuration">
            <TdLossesEditor
                tdLossesConfig={tdLossesConfig} // Pass the main config
                setTdLossesConfig={setTdLossesConfig} // Allow editor to update parent for save
                onSave={handleSaveTdLosses} // Editor calls this with its current state
                isLoading={loadingStates.tdConfigSave}
                errorMsg={errorMessages.tdConfig}
            />
          </Section>

          <Section title="Consolidated Results & Analysis">
            <Button onClick={handleGenerateConsolidated}
              disabled={loadingStates.consolidated || !modelSelectionConfig || Object.keys(modelSelectionConfig).length === 0 || !tdLossesConfig || tdLossesConfig.length === 0 || !selectedScenarioName}
              title={
                !selectedScenarioName ? "Please select a scenario first." :
                (!modelSelectionConfig || Object.keys(modelSelectionConfig).length === 0) ? "Model Selection must be configured first." :
                (!tdLossesConfig || tdLossesConfig.length === 0) ? "T&D Losses must be configured first." :
                "Generate Consolidated Results for the selected scenario"
              }
            >
              {loadingStates.consolidated ? "Generating..." : "Generate/View Consolidated Results"}
            </Button>
            <AlertMessage message={errorMessages.consolidated} type="error" />
            {consolidatedData && <PreFormatted data={consolidatedData} />}

            {consolidatedData && (
              <div style={{marginTop: '15px'}}>
                <Button onClick={handleFetchAnalysis} disabled={loadingStates.analysis}>
                  {loadingStates.analysis ? "Analyzing..." : "Get Analysis Summary"}
                </Button>
                <AlertMessage message={errorMessages.analysis} type="error" />
                {analysisSummary && <PreFormatted data={analysisSummary} />}
              </div>
            )}
          </Section>

          <Section title="Export Data">
            <Button onClick={() => handleExport('consolidated')} disabled={loadingStates.export || !consolidatedData} style={{marginRight: '10px'}}>Export Consolidated</Button>
            <Button onClick={() => handleExport('scenario_detail')} disabled={loadingStates.export || !scenarioData}>Export Scenario Detail</Button>
            <AlertMessage message={errorMessages.export} type="error" />
          </Section>
        </>
      )}
    </div>
  );
};

export default DemandVisualization;
