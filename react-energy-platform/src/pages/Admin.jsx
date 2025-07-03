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
const FormRow = ({ label, children, style }) => <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', gap: '10px', ...style }}><label style={{ minWidth: '200px', fontWeight: '500', color: '#495057', textAlign: 'left' }}>{label}:</label><div style={{flexGrow: 1}}>{children}</div></div>;
const Button = ({ children, onClick, type = "button", disabled = false, variant = "primary", style, title }) => <button title={title} type={type} onClick={onClick} disabled={disabled} style={{ padding: '10px 18px', cursor: disabled ? 'not-allowed' : 'pointer', border: 'none', borderRadius: '5px', fontWeight: 'bold', color: 'white', backgroundColor: disabled ? '#adb5bd' : (variant === 'danger' ? '#dc3545' : (variant === 'secondary' ? '#6c757d' : '#007bff')), opacity: disabled ? 0.7 : 1, minWidth: '100px', ...style }}>{children}</button>;
const AlertMessage = ({ message, type = "info" }) => { if (!message) return null; const s = {padding: '12px', margin: '15px 0', borderRadius: '5px', border: '1px solid transparent', color: type === 'error' ? '#721c24' : (type === 'success' ? '#155724' : '#0c5460'), backgroundColor: type === 'error' ? '#f8d7da' : (type === 'success' ? '#d4edda' : '#d1ecf1'), borderColor: type === 'error' ? '#f5c6cb' : (type === 'success' ? '#c3e6cb' : '#bee5eb')}; return <div style={s}>{message}</div>;};

const Admin = () => {
  const [systemInfo, setSystemInfo] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [featuresConfig, setFeaturesConfig] = useState(null);
  const [allColors, setAllColors] = useState(null);

  const [loadingStates, setLoadingStates] = useState({ info: false, health: false, features: false, colors: false, featureUpdate: {} });
  const [errorMessages, setErrorMessages] = useState({ info: null, health: null, features: null, colors: null, featureUpdate: {} });
  const [actionMessage, setActionMessage] = useState({ text: '', type: 'info' });

  const updateLoading = (key, value, id = null) => {
    if (id !== null) {
      setLoadingStates(prev => ({ ...prev, [key]: {...prev[key], [id]: value} }));
    } else {
      setLoadingStates(prev => ({ ...prev, [key]: value }));
    }
  };
  const updateError = (key, value, id = null) => {
    if (id !== null) {
      setErrorMessages(prev => ({ ...prev, [key]: {...prev[key], [id]: value} }));
    } else {
      setErrorMessages(prev => ({ ...prev, [key]: value }));
    }
  };
   const showActionMessage = (text, type = 'info') => {
    setActionMessage({text, type});
    setTimeout(() => setActionMessage({text:'', type:'info'}), 5000);
  };

  const fetchSystemInfo = useCallback(async () => {
    updateLoading('info', true); updateError('info', null);
    try {
      const response = await api.getAdminSystemInfo();
      setSystemInfo(response.data);
    } catch (err) { updateError('info', err.response?.data?.detail || err.message); }
    finally { updateLoading('info', false); }
  }, []);

  const fetchSystemHealth = useCallback(async () => {
    updateLoading('health', true); updateError('health', null);
    try {
      const response = await api.getAdminSystemHealth();
      setSystemHealth(response.data);
    } catch (err) { updateError('health', err.response?.data?.detail || err.message); }
    finally { updateLoading('health', false); }
  }, []);

  const fetchFeaturesConfig = useCallback(async (projectName = null) => {
    updateLoading('features', true); updateError('features', null);
    try {
      const response = await api.getAdminFeaturesConfig(projectName);
      setFeaturesConfig(response.data);
    } catch (err) { updateError('features', err.response?.data?.detail || err.message); }
    finally { updateLoading('features', false); }
  }, []);

  const fetchAllColors = useCallback(async () => {
    updateLoading('colors', true); updateError('colors', null);
    try {
      const response = await api.getAllColors();
      setAllColors(response.data);
    } catch (err) { updateError('colors', err.response?.data?.detail || err.message); }
    finally { updateLoading('colors', false); }
  }, []);

  useEffect(() => {
    fetchSystemInfo();
    fetchSystemHealth();
    fetchFeaturesConfig(); // Fetch global features by default
    fetchAllColors();
  }, [fetchSystemInfo, fetchSystemHealth, fetchFeaturesConfig, fetchAllColors]);

  const handleFeatureToggle = async (featureId, currentEnabledStatus, projectName = null) => {
    updateLoading('featureUpdate', true, featureId); updateError('featureUpdate', null, featureId);
    try {
      await api.updateAdminFeature(featureId, { enabled: !currentEnabledStatus }, projectName);
      showActionMessage(`Feature '${featureId}' status updated successfully!`, 'success');
      fetchFeaturesConfig(projectName); // Refresh features
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || `Failed to update feature '${featureId}'`;
      updateError('featureUpdate', errorMsg, featureId);
      showActionMessage(errorMsg, 'error');
    } finally {
      updateLoading('featureUpdate', false, featureId);
    }
  };

  const handleSystemCleanup = async () => {
    if (!window.confirm("Are you sure you want to run system cleanup (e.g., old logs)? This action might take a moment.")) return;
    showActionMessage("Starting system cleanup...", "info");
    try {
        const response = await api.triggerSystemCleanup({ type: 'all', max_age_days: 30 }); // Example payload
        showActionMessage(`Cleanup successful: ${response.data.total_files_cleaned} files cleaned. Details: ${JSON.stringify(response.data.details)}`, "success");
    } catch (err) {
        const errorMsg = err.response?.data?.detail || err.message || "System cleanup failed.";
        showActionMessage(errorMsg, "error");
    }
  };

  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px', marginBottom: '20px'}}>Admin Dashboard</h2>
      <AlertMessage message={actionMessage.text} type={actionMessage.type} />

      <Section title="System Information">
        {loadingStates.info && <p>Loading system info...</p>}
        <AlertMessage message={errorMessages.info} type="error" />
        {systemInfo && <PreFormatted data={systemInfo} />}
        <Button onClick={fetchSystemInfo} disabled={loadingStates.info} style={{marginTop: '10px'}}>Refresh Info</Button>
      </Section>

      <Section title="System Health">
        {loadingStates.health && <p>Loading system health...</p>}
        <AlertMessage message={errorMessages.health} type="error" />
        {systemHealth && <PreFormatted data={systemHealth} />}
        <Button onClick={fetchSystemHealth} disabled={loadingStates.health} style={{marginTop: '10px'}}>Refresh Health</Button>
      </Section>

      <Section title="Feature Flags Management">
        {loadingStates.features && <p>Loading feature flags...</p>}
        <AlertMessage message={errorMessages.features} type="error" />
        {featuresConfig && featuresConfig.features_by_category && Object.entries(featuresConfig.features_by_category).map(([category, features]) => (
          <div key={category}>
            <h4 style={{textTransform: 'capitalize', marginTop: '20px', color:'#555'}}>{category.replace(/_/g, ' ')}</h4>
            {features.map(feature => (
              <FormRow key={feature.id} label={feature.description || feature.id} style={{justifyContent: 'space-between'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '10px'}}>
                  <span>Status: {feature.enabled ? "Enabled" : "Disabled"}</span>
                  <Button
                    onClick={() => handleFeatureToggle(feature.id, feature.enabled)}
                    disabled={loadingStates.featureUpdate[feature.id]}
                    variant={feature.enabled ? "secondary" : "primary"}
                  >
                    {loadingStates.featureUpdate[feature.id] ? "Updating..." : (feature.enabled ? "Disable" : "Enable")}
                  </Button>
                </div>
                {errorMessages.featureUpdate[feature.id] && <AlertMessage message={errorMessages.featureUpdate[feature.id]} type="error" />}
              </FormRow>
            ))}
          </div>
        ))}
        {/* TODO: UI for project-specific feature flags if project_name context is added */}
      </Section>

      <Section title="Color Management">
        {loadingStates.colors && <p>Loading color configurations...</p>}
        <AlertMessage message={errorMessages.colors} type="error" />
        {allColors ? <PreFormatted data={allColors} /> : <p>No color configurations loaded.</p>}
        <p><em>(UI for editing colors to be implemented here. Currently shows raw JSON.)</em></p>
        {/* Example: Add button to reset colors */}
        {/* <Button onClick={async () => { await api.resetColors(); fetchAllColors(); }}>Reset All Colors</Button> */}
      </Section>

      <Section title="System Operations">
        <Button onClick={handleSystemCleanup} variant="danger">
            Perform System Cleanup (All)
        </Button>
      </Section>

    </div>
  );
};

export default Admin;
