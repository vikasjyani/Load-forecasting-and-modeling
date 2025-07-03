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
const FormRow = ({ label, children, style }) => <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', gap: '10px', ...style }}><label style={{ minWidth: '180px', fontWeight: '500', color: '#495057', textAlign: 'right', paddingRight: '10px' }}>{label}:</label><div style={{flexGrow: 1}}>{children}</div></div>;
const Select = (props) => <select {...props} style={{ padding: '10px', border: '1px solid #ced4da', borderRadius: '4px', width: '100%', boxSizing: 'border-box', ...props.style }} />;
const Input = (props) => <input {...props} style={{ padding: '10px', border: '1px solid #ced4da', borderRadius: '4px', width: '100%', boxSizing: 'border-box', ...props.style }} />;
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

const LoadProfileAnalysis = () => {
  const [projectName, setProjectName] = useState("Default_Project");
  const [availableProfiles, setAvailableProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState('');
  const [statisticalSummary, setStatisticalSummary] = useState(null);
  const [analysisUnit, setAnalysisUnit] = useState('kW');

  const [analysisTypeToRun, setAnalysisTypeToRun] = useState('peak_analysis'); // Example
  const [analysisParams, setAnalysisParams] = useState('{}'); // JSON string
  const [customAnalysisResult, setCustomAnalysisResult] = useState(null);

  const [loadingStates, setLoadingStates] = useState({ profiles: false, summary: false, customAnalysis: false });
  const [errorMessages, setErrorMessages] = useState({ profiles: null, summary: null, customAnalysis: null });
  const [actionMessage, setActionMessage] = useState({ text: '', type: 'info' });

  const updateLoading = (key, value) => setLoadingStates(prev => ({ ...prev, [key]: value }));
  const updateError = (key, value) => setErrorMessages(prev => ({ ...prev, [key]: value }));
  const showActionMessage = (text, type = 'info') => { setActionMessage({text, type}); setTimeout(() => setActionMessage({text:'', type:'info'}), 5000);};

  const fetchAvailableProfiles = useCallback(async () => {
    if (!projectName) return;
    updateLoading('profiles', true); updateError('profiles', null);
    try {
      const response = await api.listAvailableProfilesForAnalysis(projectName);
      setAvailableProfiles(response.data || []);
      if (response.data && response.data.length > 0) {
        // Optionally auto-select first profile
        // setSelectedProfileId(response.data[0].profile_id);
      } else {
        setSelectedProfileId('');
      }
    } catch (err) {
      updateError('profiles', err.response?.data?.detail || err.message || "Failed to fetch available profiles");
    } finally {
      updateLoading('profiles', false);
    }
  }, [projectName]);

  useEffect(() => {
    fetchAvailableProfiles();
  }, [fetchAvailableProfiles]);

  const fetchStatisticalSummary = useCallback(async () => {
    if (!projectName || !selectedProfileId) {
        setStatisticalSummary(null);
        return;
    }
    updateLoading('summary', true); updateError('summary', null);
    try {
      const response = await api.getStatisticalSummary(projectName, selectedProfileId, analysisUnit);
      setStatisticalSummary(response.data);
    } catch (err) {
      updateError('summary', err.response?.data?.detail || err.message || "Failed to fetch statistical summary");
      setStatisticalSummary(null);
    } finally {
      updateLoading('summary', false);
    }
  }, [projectName, selectedProfileId, analysisUnit]);

  useEffect(() => {
    // Fetch summary when profile or unit changes
    if(selectedProfileId) fetchStatisticalSummary();
  }, [selectedProfileId, analysisUnit, fetchStatisticalSummary]);


  const handlePerformAnalysis = async (e) => {
    e.preventDefault();
    if (!projectName || !selectedProfileId || !analysisTypeToRun) {
        showActionMessage("Project, Profile ID, and Analysis Type are required.", "error");
        return;
    }
    updateLoading('customAnalysis', true); updateError('customAnalysis', null); setCustomAnalysisResult(null);
    let parsedParams = null;
    try {
        if(analysisParams.trim()) parsedParams = JSON.parse(analysisParams);
    } catch (jsonErr) {
        updateError('customAnalysis', "Invalid JSON for Analysis Parameters.");
        updateLoading('customAnalysis', false);
        return;
    }

    try {
        const response = await api.performLoadProfileAnalysis(projectName, selectedProfileId, analysisTypeToRun, parsedParams);
        setCustomAnalysisResult(response.data);
        showActionMessage(`${analysisTypeToRun} completed successfully.`, "success");
    } catch (err) {
        const errorMsg = err.response?.data?.detail || err.message || `Failed to perform ${analysisTypeToRun}`;
        updateError('customAnalysis', errorMsg);
        showActionMessage(errorMsg, "error");
    } finally {
        updateLoading('customAnalysis', false);
    }
  };

  const analysisTypesAvailable = ['peak_analysis', 'seasonal_analysis', 'duration_curve', 'heatmap', 'variability']; // Example types

  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px', marginBottom: '20px'}}>
        Load Profile Analysis: Project <strong>{projectName}</strong>
      </h2>
      <AlertMessage message={actionMessage.text} type={actionMessage.type} />

      <Section title="Select Load Profile">
        {loadingStates.profiles && <p>Loading available profiles...</p>}
        <AlertMessage message={errorMessages.profiles} type="error" />
        {availableProfiles.length > 0 ? (
          <FormRow label="Choose Profile for Analysis">
            <Select value={selectedProfileId} onChange={e => setSelectedProfileId(e.target.value)}>
              <option value="">-- Select a Profile --</option>
              {availableProfiles.map(p => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.profile_id} (Method: {p.method_used || 'N/A'}, Valid: {p.quick_validation_status?.valid ? 'Yes' : 'No'})
                </option>
              ))}
            </Select>
          </FormRow>
        ) : (
          !loadingStates.profiles && <p>No load profiles found for this project or failed to load.</p>
        )}
      </Section>

      {selectedProfileId && (
        <>
          <Section title={`Statistical Summary for Profile: ${selectedProfileId}`}>
            <FormRow label="Display Unit">
                <Select value={analysisUnit} onChange={e => setAnalysisUnit(e.target.value)}>
                    <option value="kW">kW</option>
                    <option value="MW">MW</option>
                    <option value="GW">GW</option>
                </Select>
            </FormRow>
            {loadingStates.summary && <p>Loading statistical summary...</p>}
            <AlertMessage message={errorMessages.summary} type="error" />
            {statisticalSummary && <PreFormatted data={statisticalSummary} />}
          </Section>

          <Section title="Perform Specific Analysis">
            <form onSubmit={handlePerformAnalysis} style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
              <FormRow label="Analysis Type">
                <Select value={analysisTypeToRun} onChange={e => setAnalysisTypeToRun(e.target.value)}>
                  {analysisTypesAvailable.map(type => <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>)}
                </Select>
              </FormRow>
              <FormRow label="Analysis Parameters (JSON)">
                <textarea
                  rows="3"
                  value={analysisParams}
                  onChange={e => setAnalysisParams(e.target.value)}
                  placeholder='e.g., {"period": "monthly"} or leave empty if not needed'
                  style={{width: '100%', fontFamily: 'monospace', padding: '8px', border: '1px solid #ccc', boxSizing: 'border-box'}}
                />
              </FormRow>
              <Button type="submit" disabled={loadingStates.customAnalysis}>
                {loadingStates.customAnalysis ? 'Analyzing...' : 'Run Analysis'}
              </Button>
              <AlertMessage message={errorMessages.customAnalysis} type="error" />
            </form>
            {customAnalysisResult && (
              <div style={{marginTop: '15px'}}>
                <h4>Result for {analysisTypeToRun.replace(/_/g, ' ')}:</h4>
                <PreFormatted data={customAnalysisResult} />
              </div>
            )}
          </Section>
        </>
      )}
      {/* Placeholders for other analysis UIs: Comparison, Batch, Reports etc. */}
    </div>
  );
};

export default LoadProfileAnalysis;
