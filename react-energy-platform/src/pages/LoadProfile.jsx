import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';

// --- UI Helper Components (can be moved to a common UI components directory) ---

const Section = ({ title, children, style }) => (
  <section style={{
    marginBottom: '25px',
    padding: '20px',
    border: '1px solid #e0e0e0',
    borderRadius: '8px',
    backgroundColor: '#f9f9f9',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
    ...style
  }}>
    <h3 style={{ marginTop: 0, borderBottom: '2px solid #007bff', paddingBottom: '10px', color: '#0056b3' }}>{title}</h3>
    {children}
  </section>
);

const PreFormatted = ({ data, style }) => (
  <pre style={{
    backgroundColor: '#e9ecef',
    padding: '15px',
    borderRadius: '5px',
    overflowX: 'auto',
    border: '1px solid #ced4da',
    fontSize: '0.85em',
    ...style
  }}>
    {JSON.stringify(data, null, 2)}
  </pre>
);

const Table = ({ headers, data, renderRow, caption }) => (
  <div style={{overflowX: 'auto'}}>
    <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9em'}}>
      {caption && <caption style={{ captionSide: 'top', textAlign: 'left', paddingBottom: '10px', fontWeight: 'bold', color: '#333' }}>{caption}</caption>}
      <thead>
        <tr>
          {headers.map(header => (
            <th key={header} style={{
              border: '1px solid #ddd',
              padding: '10px 12px',
              textAlign: 'left',
              backgroundColor: '#007bff',
              color: 'white',
              textTransform: 'capitalize'
            }}>
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

const FormRow = ({ label, children }) => (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px', gap: '10px' }}>
        <label style={{ minWidth: '200px', fontWeight: '500', color: '#495057' }}>{label}:</label>
        {children}
    </div>
);

const Input = (props) => (
    <input {...props} style={{padding: '8px', border: '1px solid #ced4da', borderRadius: '4px', flexGrow: 1, ...props.style}} />
);

const Select = (props) => (
    <select {...props} style={{padding: '8px', border: '1px solid #ced4da', borderRadius: '4px', flexGrow: 1, ...props.style}} />
);

const Button = ({ children, onClick, type = "button", disabled = false, variant = "primary", style }) => (
    <button
        type={type}
        onClick={onClick}
        disabled={disabled}
        style={{
            padding: '10px 18px',
            cursor: disabled ? 'not-allowed' : 'pointer',
            border: 'none',
            borderRadius: '5px',
            fontWeight: 'bold',
            color: 'white',
            backgroundColor: disabled ? '#adb5bd' : (variant === 'danger' ? '#dc3545' : '#007bff'),
            opacity: disabled ? 0.7 : 1,
            minWidth: '100px',
            ...style
        }}
    >
        {children}
    </button>
);

const AlertMessage = ({ message, type = "info" }) => {
    if (!message) return null;
    const alertStyles = {
        padding: '12px',
        margin: '15px 0',
        borderRadius: '5px',
        border: '1px solid transparent',
    };
    if (type === 'error') {
        alertStyles.color = '#721c24';
        alertStyles.backgroundColor = '#f8d7da';
        alertStyles.borderColor = '#f5c6cb';
    } else if (type === 'success') {
        alertStyles.color = '#155724';
        alertStyles.backgroundColor = '#d4edda';
        alertStyles.borderColor = '#c3e6cb';
    } else { // info
        alertStyles.color = '#0c5460';
        alertStyles.backgroundColor = '#d1ecf1';
        alertStyles.borderColor = '#bee5eb';
    }
    return <div style={alertStyles}>{message}</div>;
};


const LoadProfile = () => {
  const [projectName, setProjectName] = useState("Default_Project"); // Hardcoded for now

  // Data states
  const [mainData, setMainData] = useState(null); // To store data from getLoadProfileMainData
  const [templateInfo, setTemplateInfo] = useState(null);
  const [availableBaseYears, setAvailableBaseYears] = useState([]);
  // savedProfiles will be part of mainData, no need for separate state if mainData structure is good
  const [selectedProfileData, setSelectedProfileData] = useState(null);

  // Form states for generation
  const [generationType, setGenerationType] = useState('base_profile');
  const [baseYear, setBaseYear] = useState('');
  const [startFy, setStartFy] = useState('');
  const [endFy, setEndFy] = useState('');
  const [demandSource, setDemandSource] = useState('template');
  const [scenarioName, setScenarioName] = useState('');
  const [customProfileName, setCustomProfileName] = useState('');
  const [generationMessage, setGenerationMessage] = useState({ text: '', type: 'info' }); // For success/error messages

  // UI states - more granular loading/error states
  const [loadingStates, setLoadingStates] = useState({
    mainData: false, templateInfo: false, baseYears: false,
    generation: false, profileDetails: false, templateUpload: false,
  });
  const [errorMessages, setErrorMessages] = useState({
    mainData: null, templateInfo: null, baseYears: null,
    generation: null, profileDetails: null, templateUpload: null,
  });
  const [uploadStatusMessage, setUploadStatusMessage] = useState('');


  const updateLoading = (key, value) => setLoadingStates(prev => ({ ...prev, [key]: value }));
  const updateError = (key, value) => setErrorMessages(prev => ({ ...prev, [key]: value }));


  const fetchMainData = useCallback(async () => {
    updateLoading('mainData', true);
    updateError('mainData', null);
    try {
      const response = await api.getLoadProfileMainData(projectName);
      setMainData(response.data);
      // Assuming saved_profiles and template_info are part of response.data as per service
      if(response.data?.template_info) setTemplateInfo(response.data.template_info);
      fetchAvailableBaseYears(); // Fetch base years after main data (which might include template info)
    } catch (err) {
      console.error("Error fetching main load profile data:", err);
      updateError('mainData', err.response?.data?.detail || err.message || 'Failed to fetch main data');
    } finally {
      updateLoading('mainData', false);
    }
  }, [projectName]); // Removed fetchAvailableBaseYears from dependency array here

  const fetchAvailableBaseYears = useCallback(async () => {
    updateLoading('baseYears', true);
    updateError('baseYears', null);
    try {
      const response = await api.getAvailableBaseYears(projectName);
      setAvailableBaseYears(response.data.available_base_years || []);
    } catch (err) {
      console.error("Error fetching available base years:", err);
      updateError('baseYears', err.response?.data?.detail || err.message || 'Failed to fetch base years');
    } finally {
      updateLoading('baseYears', false);
    }
  }, [projectName]);

  const fetchTemplateInfo = useCallback(async () => {
    updateLoading('templateInfo', true);
    updateError('templateInfo', null);
    try {
        const response = await api.getTemplateInfo(projectName);
        setTemplateInfo(response.data);
        // If template info is fetched successfully, it might affect base years
        fetchAvailableBaseYears();
    } catch (err) {
        const errorDetail = err.response?.data?.detail || err.message || "Failed to fetch template info";
        updateError('templateInfo', errorDetail);
        // Set templateInfo to reflect the error state for display
        setTemplateInfo(prev => ({ ...prev, error: errorDetail, file_exists: false }));
    } finally {
        updateLoading('templateInfo', false);
    }
  }, [projectName, fetchAvailableBaseYears]); // Added fetchAvailableBaseYears to deps

  useEffect(() => {
    // Fetch initial data for the page; mainData includes saved profiles and basic template info.
    fetchMainData();
    // Fetch detailed template info (which also triggers base years fetch)
    fetchTemplateInfo();
  }, [fetchMainData, fetchTemplateInfo]); // Only these two should be dependencies here.


  const handleGenerateProfile = async (e) => {
    e.preventDefault();
    updateLoading('generation', true);
    updateError('generation', null);
    setGenerationMessage({ text: '', type: 'info' });

    const payload = {
      start_fy: parseInt(startFy),
      end_fy: parseInt(endFy),
      demand_source: demandSource,
      scenario_name: demandSource === 'scenario' ? scenarioName : null,
      custom_name: customProfileName || null, // Send null if empty
    };

    if (generationType === 'base_profile') {
      if (!baseYear) {
        setGenerationMessage({ text: "Base Year is required for Base Profile Scaling.", type: 'error' });
        updateLoading('generation', false);
        return;
      }
      payload.base_year = parseInt(baseYear);
    }

    try {
      let response;
      if (generationType === 'base_profile') {
        response = await api.generateBaseProfile(projectName, payload);
      } else {
        response = await api.generateStlProfile(projectName, payload);
      }
      setGenerationMessage({ text: `Profile generation successful: ${response.data.profile_id}`, type: 'success' });
      fetchMainData(); // Refresh list of saved profiles
      // Reset form fields
      setCustomProfileName('');
      setStartFy('');
      setEndFy('');
      setBaseYear('');
      setScenarioName('');
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Profile generation failed';
      updateError('generation', errorMsg);
      setGenerationMessage({ text: `Error: ${errorMsg}`, type: 'error' });
    } finally {
      updateLoading('generation', false);
    }
  };

  const handleViewProfile = async (profileId) => {
    updateLoading('profileDetails', true);
    updateError('profileDetails', null);
    setSelectedProfileData(null); // Clear previous details
    try {
      const response = await api.getLoadProfileData(projectName, profileId);
      setSelectedProfileData(response.data);
    } catch (err) {
      console.error(`Error fetching profile ${profileId}:`, err);
      updateError('profileDetails', err.response?.data?.detail || err.message || 'Failed to fetch profile details');
    } finally {
      updateLoading('profileDetails', false);
    }
  };

  const handleDeleteProfile = async (profileId) => {
    if (!window.confirm(`Are you sure you want to delete profile ${profileId}?`)) return;
    try {
      await api.deleteLoadProfile(projectName, profileId);
      setGenerationMessage({text: `Profile ${profileId} deleted successfully.`, type: 'success'});
      fetchMainData(); // Refresh list
      if(selectedProfileData?.metadata?.profile_id === profileId) {
        setSelectedProfileData(null); // Clear details if deleted profile was being viewed
      }
    } catch (err) {
      const errorMsg = err.response?.data?.detail || err.message || 'Error deleting profile';
      setGenerationMessage({text: errorMsg, type: 'error'});
      updateError('generation', errorMsg); // Use generation error slot for this feedback too
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    updateLoading('templateUpload', true);
    setUploadStatusMessage('Uploading...');
    updateError('templateUpload', null);
    try {
        const response = await api.uploadLoadProfileTemplate(projectName, file);
        setUploadStatusMessage(`Upload successful: ${response.data.file_info?.name}`);
        fetchTemplateInfo(); // This will also trigger fetchAvailableBaseYears
    } catch (err) {
        const errorMsg = err.response?.data?.detail || err.message || "Upload Failed";
        setUploadStatusMessage(`Upload failed: ${errorMsg}`);
        updateError('templateUpload', errorMsg);
    } finally {
        updateLoading('templateUpload', false);
        event.target.value = null; // Reset file input
    }
  };


  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px'}}>
        Load Profile Management for Project: <strong>{projectName}</strong>
      </h2>

      <Section title="Load Curve Template">
        {loadingStates.templateInfo ? <p>Loading template info...</p> : templateInfo && templateInfo.file_exists ? <PreFormatted data={templateInfo} /> : <p style={{color: 'orange'}}>Template file 'load_curve_template.xlsx' not found or not yet loaded. Please upload one.</p>}
        <AlertMessage message={errorMessages.templateInfo} type="error" />
        <div style={{marginTop: '10px'}}>
            <Input type="file" onChange={handleFileUpload} accept=".xlsx" disabled={loadingStates.templateUpload || loadingStates.templateInfo} />
        </div>
        {loadingStates.templateUpload && <p>Uploading...</p>}
        <AlertMessage message={uploadStatusMessage} type={errorMessages.templateUpload ? "error" : "success"} />
      </Section>

      <Section title="Available Base Years (from Template)">
        {loadingStates.baseYears ? <p>Loading base years...</p> :
          (availableBaseYears.length > 0 ?
            <ul style={{listStyleType: 'circle', paddingLeft: '20px'}}>{availableBaseYears.map(year => <li key={year}>{year}</li>)}</ul> :
            <p>No base years available. This might be due to a missing or invalid template, or the template has no processable historical data.</p>)
        }
        <AlertMessage message={errorMessages.baseYears} type="error" />
      </Section>

      <Section title="Available Demand Scenarios (from Demand Projection)">
        {mainData?.available_scenarios?.length > 0 ? (
            <Select value={scenarioName} onChange={e => setScenarioName(e.target.value)} disabled={demandSource !== 'scenario'}>
                <option value="">Select a Demand Scenario</option>
                {mainData.available_scenarios.map(sc => (
                    <option key={sc.name} value={sc.name}>{sc.name} (Last Modified: {new Date(sc.file_info?.modified_iso).toLocaleDateString()})</option>
                ))}
            </Select>
        ) : <p>No demand scenarios found. Please generate demand projections first.</p>}
      </Section>


      <Section title="Generate New Load Profile">
        <form onSubmit={handleGenerateProfile} style={{display: 'flex', flexDirection: 'column', gap: '15px'}}>
          <FormRow label="Generation Type">
            <Select value={generationType} onChange={e => setGenerationType(e.target.value)}>
              <option value="base_profile">Base Profile Scaling</option>
              <option value="stl_profile">STL Decomposition</option>
            </Select>
          </FormRow>
          {generationType === 'base_profile' && (
            <FormRow label="Base Year (from Template)">
              <Select value={baseYear} onChange={e => setBaseYear(e.target.value)} required={generationType === 'base_profile'}>
                <option value="">Select Base Year</option>
                {availableBaseYears.map(year => <option key={year} value={year}>{year}</option>)}
              </Select>
            </FormRow>
          )}
          <FormRow label="Start Financial Year">
            <Input type="number" value={startFy} onChange={e => setStartFy(e.target.value)} placeholder="e.g., 2023" required />
          </FormRow>
          <FormRow label="End Financial Year">
            <Input type="number" value={endFy} onChange={e => setEndFy(e.target.value)} placeholder="e.g., 2030" required />
          </FormRow>
          <FormRow label="Demand Source">
            <Select value={demandSource} onChange={e => setDemandSource(e.target.value)}>
              <option value="template">From Template Total Demand</option>
              <option value="scenario">From Demand Projection Scenario</option>
            </Select>
          </FormRow>
          {demandSource === 'scenario' && (
            <FormRow label="Scenario Name">
              <Select value={scenarioName} onChange={e => setScenarioName(e.target.value)} required={demandSource === 'scenario'}>
                 <option value="">Select a Scenario</option>
                 {mainData?.available_scenarios?.map(sc => (
                    <option key={sc.name} value={sc.name}>{sc.name}</option>
                 ))}
              </Select>
            </FormRow>
          )}
          <FormRow label="Output Profile Frequency">
             <Select value={customProfileName.frequency /* Assuming frequency is part of a config object */} onChange={e => setCustomProfileName(prev => ({...prev, frequency: e.target.value}))}>
                <option value="hourly">Hourly</option>
                <option value="15min">15-minute</option>
                <option value="30min">30-minute</option>
                {/* <option value="daily">Daily</option> */} {/* Daily might need different logic */}
             </Select>
          </FormRow>
           <FormRow label="Custom Profile Name (Optional)">
            <Input type="text" value={customProfileName.name || ''} onChange={e => setCustomProfileName(prev => ({...prev, name: e.target.value}))} placeholder="e.g., MySummerProfile_HighGrowth" />
          </FormRow>
          {/* TODO: Add inputs for STL params, constraints, LF improvement if stl_profile selected */}

          <div style={{marginTop: '10px'}}>
            <Button type="submit" disabled={loadingStates.generation || !templateInfo?.file_exists}>
              {loadingStates.generation ? 'Generating...' : 'Generate Profile'}
            </Button>
            {!templateInfo?.file_exists && <span style={{color: 'red', marginLeft: '10px'}}>Template must be uploaded first.</span>}
          </div>
          <AlertMessage message={generationMessage.text} type={generationMessage.type} />
        </form>
      </Section>

      <Section title="Saved Load Profiles">
        {loadingStates.mainData ? <p>Loading profiles...</p> : (
          mainData && mainData.saved_profiles && mainData.saved_profiles.length > 0 ? (
            <Table
              headers={['ID', 'Method', 'Created At', 'Years', 'Frequency', 'File Size (MB)', 'Actions']}
              data={mainData.saved_profiles}
              renderRow={(profile, index) => (
                <tr key={profile.profile_id || index} style={{backgroundColor: index % 2 === 0 ? 'white' : '#f0f8ff'}}>
                  <td style={{border: '1px solid #ddd', padding: '10px 12px'}}>{profile.profile_id}</td>
                  <td style={{border: '1px solid #ddd', padding: '10px 12px'}}>{profile.method_used || profile.metadata?.method_used}</td>
                  <td style={{border: '1px solid #ddd', padding: '10px 12px'}}>{profile.created_at ? new Date(profile.created_at).toLocaleString() : (profile.metadata?.created_at ? new Date(profile.metadata.created_at).toLocaleString() : 'N/A')}</td>
                  <td style={{border: '1px solid #ddd', padding: '10px 12px'}}>{(profile.years_generated || profile.metadata?.years_generated)?.join(', ')}</td>
                  <td style={{border: '1px solid #ddd', padding: '10px 12px'}}>{profile.frequency || profile.metadata?.frequency}</td>
                  <td style={{border: '1px solid #ddd', padding: '10px 12px'}}>{profile.file_info?.size_mb !== undefined ? `${profile.file_info.size_mb} MB` : 'N/A'}</td>
                  <td style={{border: '1px solid #ddd', padding: '10px 12px', minWidth: '250px'}}>
                    <Button onClick={() => handleViewProfile(profile.profile_id)} style={{marginRight: '8px', marginBottom: '5px'}}>View Data</Button>
                    <Button onClick={() => handleDownloadProfile(profile.profile_id)} style={{marginRight: '8px', marginBottom: '5px'}}>Download</Button>
                    <Button onClick={() => handleDeleteProfile(profile.profile_id)} variant="danger">Delete</Button>
                  </td>
                </tr>
              )}
            />
          ) : <p>No saved profiles found for this project.</p>
        )}
        <AlertMessage message={errorMessages.mainData} type="error" />
      </Section>

      {selectedProfileData && (
        <Section title={`Data for Profile: ${selectedProfileData.metadata?.profile_id || selectedProfileData.profile_id}`}>
          {loadingStates.profileDetails ? <p>Loading details...</p> : <PreFormatted data={selectedProfileData} />}
          <AlertMessage message={errorMessages.profileDetails} type="error" />
        </Section>
      )}

    </div>
  );
};

export default LoadProfile;
