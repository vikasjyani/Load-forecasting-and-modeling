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

// Attempt to import chart components
// User will need to install these: npm install chart.js react-chartjs-2
import { Bar, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  TimeScale, // For time-series data
  TimeSeriesScale, // For time-series data if using that specific scale type
  Filler, // For area charts
} from 'chart.js';
import 'chartjs-adapter-date-fns'; // If using date-fns for time scale

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
  TimeSeriesScale,
  Filler
);


const renderExtractedDataTable = (dataArray, keyPrefix, headers) => {
    // Helper to truncate long strings or stringify objects/arrays for table cells
    const formatCellData = (cellData) => {
        if (typeof cellData === 'object' && cellData !== null) {
            const str = JSON.stringify(cellData);
            return str.length > 75 ? str.substring(0, 72) + "..." : str;
        }
        const strCellData = String(cellData);
        return strCellData.length > 75 ? strCellData.substring(0, 72) + "..." : strCellData;
    };

    return (
      <Table
        headers={headers}
        data={dataArray}
        renderRow={(row, rowIndex) => (
          <tr key={`${keyPrefix}-${rowIndex}`} style={{backgroundColor: rowIndex % 2 === 0 ? 'white' : '#f0f8ff'}}>
            {headers.map(header => (
              <td
                key={`${keyPrefix}-${rowIndex}-${header}`}
                title={typeof row[header] === 'object' ? JSON.stringify(row[header]) : String(row[header])} // Full data on hover
                style={{border: '1px solid #ddd', padding: '8px', whiteSpace: 'nowrap', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis'}}
              >
                {formatCellData(row[header])}
              </td>
            ))}
          </tr>
        )}
      />
    );
  };

  const renderExtractedDataCharts = (extractedData) => {
    if (!extractedData || !extractedData.data || !extractedData.metadata) return <p>No chart data available or metadata missing.</p>;

    const dataContent = extractedData.data;
    const funcName = extractedData.metadata.extraction_function;
    const providedColors = extractedData.colors || {}; // Colors from backend if available

    const chartHeight = '400px';
    const chartContainerStyle = { height: chartHeight, marginBottom: '30px', padding: '10px', border: '1px solid #eee', borderRadius: '5px' };

    // Default chart options
    const defaultOptions = (titleText, xLabel = 'Category', yLabel = 'Value') => ({
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { position: 'top' },
            title: { display: true, text: titleText },
            tooltip: { mode: 'index', intersect: false }
        },
        scales: {
            x: { title: { display: true, text: xLabel }, stacked: false }, // Default to non-stacked
            y: { title: { display: true, text: yLabel }, stacked: false, beginAtZero: true }
        }
    });

    if (funcName === 'dispatch_data_payload_former' && dataContent.generation && dataContent.generation.length > 0) {
        const generationData = dataContent.generation;
        // Ensure timestamps are correctly parsed if they are strings
        const timestamps = (dataContent.timestamps || generationData.map(d => d.index || d.timestamp)).map(ts => new Date(ts));

        const carrierNames = Object.keys(generationData[0]).filter(key => key !== 'index' && key !== 'timestamp' && typeof generationData[0][key] === 'number');

        const datasets = carrierNames.map(carrier => ({
            label: carrier,
            data: generationData.map(d => d[carrier]),
            backgroundColor: providedColors[carrier] || getRandomColor(),
            borderColor: providedColors[carrier] || getRandomColor(), // Optional: darker border
            borderWidth: 1,
        }));

        const chartData = { labels: timestamps, datasets };
        const options = defaultOptions('Generation Dispatch by Carrier', 'Timestamp', `Energy (${extractedData.metadata.unit || 'MWh'})`);
        options.scales.x = { type: 'time', time: { unit: 'hour', tooltipFormat: 'MMM d, yyyy HH:mm' }, title: { display: true, text: 'Timestamp' }, stacked: true };
        options.scales.y.stacked = true;

        return <div style={chartContainerStyle}><Bar data={chartData} options={options} /></div>;
    }

    if (funcName === 'carrier_capacity_payload_former' && dataContent.by_carrier && dataContent.by_carrier.length > 0) {
        const capacityByCarrier = dataContent.by_carrier;
        const labels = capacityByCarrier.map(item => item.Carrier);
        const dataValues = capacityByCarrier.map(item => item.Capacity);
        const unit = extractedData.metadata.unit || capacityByCarrier[0]?.Unit || 'MW';

        const chartData = {
            labels: labels,
            datasets: [{
                label: `Installed Capacity`,
                data: dataValues,
                backgroundColor: labels.map(label => providedColors[label] || getRandomColor()),
            }]
        };
        const options = defaultOptions(`Installed Capacity by Carrier (${unit})`, `Capacity (${unit})`, 'Carrier');
        options.indexAxis = 'y'; // Horizontal bar chart
        options.plugins.legend.display = false;

        return <div style={{...chartContainerStyle, height: `${100 + labels.length * 25}px` }}><Bar data={chartData} options={options} /></div>;
    }

    if (funcName === 'new_capacity_additions_payload_former' && dataContent.new_capacity && dataContent.new_capacity.length > 0) {
        const newCapacityData = dataContent.new_capacity;
        const labels = newCapacityData.map(item => `${item.Carrier} (${item.Region || 'N/A'})`);
        const dataValues = newCapacityData.map(item => item.New_Capacity);
        const unit = extractedData.metadata.unit || newCapacityData[0]?.Unit || 'MW';

        const chartData = {
            labels: labels,
            datasets: [{
                label: `New Capacity Additions`,
                data: dataValues,
                backgroundColor: newCapacityData.map(item => providedColors[item.Carrier] || getRandomColor()),
            }]
        };
        const options = defaultOptions(`New Capacity Additions (${unit})`, `Capacity Added (${unit})`, 'Technology/Region');
        options.indexAxis = 'y';
        options.plugins.legend.display = false;
        return <div style={{...chartContainerStyle, height: `${100 + labels.length * 25}px` }}><Bar data={chartData} options={options} /></div>;
    }

    if (funcName === 'emissions_payload_former' && dataContent.emissions_timeseries && dataContent.emissions_timeseries.length > 0) {
        const emissionsData = dataContent.emissions_timeseries;
        const timestamps = (dataContent.timestamps || emissionsData.map(d => d.index || d.timestamp)).map(ts => new Date(ts));
        const unit = extractedData.metadata.unit || 'tCO2';

        // Assuming emissions_timeseries is an array of objects like [{timestamp: '...', 'CO2': 123, 'SOx': 45}, ...]
        // Or if it's simpler: [{timestamp: '...', value: 123}]
        // For this example, let's assume a 'total_emissions' key or similar.
        // If multiple pollutants, would need to adapt like dispatch.
        const pollutantKey = Object.keys(emissionsData[0]).find(k => k !== 'index' && k !== 'timestamp' && typeof emissionsData[0][k] === 'number');

        if (!pollutantKey) return <p>Could not determine pollutant data key for emissions chart.</p>;

        const datasets = [{
            label: `${pollutantKey.replace(/_/g, ' ')} Emissions`,
            data: emissionsData.map(d => d[pollutantKey]),
            borderColor: 'rgba(255, 99, 132, 0.8)',
            backgroundColor: 'rgba(255, 99, 132, 0.5)',
            tension: 0.1,
            fill: true,
        }];

        const chartData = { labels: timestamps, datasets };
        const options = defaultOptions(`${pollutantKey.replace(/_/g, ' ')} Emissions Over Time`, 'Timestamp', `Emissions (${unit})`);
        options.scales.x = { type: 'time', time: { unit: 'day', tooltipFormat: 'MMM d, yyyy HH:mm' }, title: { display: true, text: 'Timestamp' }};

        return <div style={chartContainerStyle}><Line data={chartData} options={options} /></div>;
    }


    if (funcName === 'extract_api_prices_data_payload_former' && dataContent.price_duration_curve && dataContent.price_duration_curve.length > 0) {
        const priceData = dataContent.price_duration_curve;
        const unit = extractedData.metadata.unit_price || 'EUR/MWh';
        const chartData = {
            labels: priceData.map(p => p.duration_hours),
            datasets: [{
                label: `Price Duration Curve (${unit})`,
                data: priceData.map(p => p.price_value),
                borderColor: 'rgba(153, 102, 255, 0.8)',
                backgroundColor: 'rgba(153, 102, 255, 0.5)',
                tension: 0.1,
                pointRadius: 0, // Cleaner for duration curves
            }]
        };
        const options = defaultOptions('Price Duration Curve', 'Duration (Hours)', `Price (${unit})`);
        options.scales.x.type = 'linear'; // Duration is linear
        return <div style={chartContainerStyle}><Line data={chartData} options={options} /></div>;
    }


    return <p>No specific chart preview available for '{funcName}'. View raw data in tables below.</p>;
  };

  // Helper to generate random colors for charts if not provided - ensure it's defined if used.
  const getRandomColor = () => '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');


  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px', marginBottom: '20px'}}>
        PyPSA Power System Modeling: Project <Input type="text" value={projectName} onChange={e => setProjectName(e.target.value)} placeholder="Default_Project" />
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
          !loadingStates.scenarios && <p>No PyPSA scenario folders found for project '{projectName}'. Create scenarios via 'Run Simulation' or ensure they exist.</p>
        )}
         <Button onClick={fetchAvailableScenarios} disabled={loadingStates.scenarios || !projectName} style={{marginTop:'10px'}}>Refresh Scenarios</Button>
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
          <Button type="submit" disabled={loadingStates.run || !projectName || !runScenarioName || (jobId && jobStatus?.status !== 'COMPLETED' && jobStatus?.status !== 'FAILED' && jobStatus?.status !== 'CANCELLED')}>
            {loadingStates.run ? 'Starting...' : (jobId && jobStatus?.status !== 'COMPLETED' && jobStatus?.status !== 'FAILED' && jobStatus?.status !== 'CANCELLED' ? `Running (${jobStatus?.status})...` : 'Run Simulation')}
          </Button>
          <AlertMessage message={errorMessages.run} type="error" />
        </form>
      </Section>

      {jobId && (
        <Section title={`Job Status (ID: ${jobId})`}>
          {loadingStates.status && !jobStatus?.status && <p>Fetching status...</p>}
          <AlertMessage message={errorMessages.status} type="error" />
          {jobStatus ? <PreFormatted data={jobStatus} /> : <p>No status data yet.</p>}
          <h4>Job Log Highlights:</h4>
          {jobLog.length > 0 ? (
            <ul style={{fontSize: '0.8em', maxHeight: '200px', overflowY: 'auto', backgroundColor: '#f8f9fa', padding: '10px', border: '1px solid #eee', borderRadius: '4px'}}>
              {jobLog.map((logEntry, index) => <li key={index} style={{borderBottom: '1px dotted #ccc', paddingBottom: '3px', marginBottom: '3px'}}>{logEntry}</li>)}
            </ul>
          ) : <p>No log entries yet.</p>}
        </Section>
      )}

      {selectedNetworkFile && selectedScenario && projectName && (
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
            <AlertMessage message={errorMessages.extraction} type="error" />
          </form>
          {extractedPyPSAData && (
            <div style={{marginTop: '20px'}}>
              <h4 style={{color:'#0056b3'}}>Extracted Data Preview:</h4>
              <AlertMessage message={extractedPyPSAData.metadata?.error} type="error" />
              {/* Render Charts First */}
              {extractedPyPSAData.data && renderExtractedDataCharts(extractedPyPSAData)}
              {/* Then Render Tables */}
              {extractedPyPSAData.data && renderExtractedDataTables(extractedPyPSAData)}

              <details style={{marginTop: '15px'}}>
                <summary style={{cursor: 'pointer', fontWeight: 'bold', color: '#0056b3'}}>View Full Extraction Response (JSON)</summary>
                <PreFormatted data={extractedPyPSAData} />
              </details>
            </div>
          )}
        </Section>
      )}
    </div>
  );
};

export default PyPSAModeling;
