import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale,
} from 'chart.js';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  TimeScale
);

// UI Helper Components (assuming they are defined as before)
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
const Table = ({ headers, data, renderRow, caption, keyPrefix = "row" }) => (
  <div style={{overflowX: 'auto', margin: '15px 0'}}>
    <table style={{width: '100%', borderCollapse: 'collapse', fontSize: '0.9em'}}>
      {caption && <caption style={{ captionSide: 'top', textAlign: 'left', paddingBottom: '10px', fontWeight: 'bold', color: '#333' }}>{caption}</caption>}
      <thead>
        <tr>
          {headers.map(header => (
            <th key={header.key || header} style={{ border: '1px solid #ddd', padding: '10px 12px', textAlign: 'left', backgroundColor: '#007bff', color: 'white', textTransform: 'capitalize' }}>
              {header.label || header.replace(/_/g, ' ')}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((item, index) => renderRow(item, `${keyPrefix}-${index}`))}
      </tbody>
    </table>
  </div>
);

// Chart Components (PeakAnalysisDisplay, DurationCurveChart, SeasonalAnalysisCharts - assumed from previous steps)
const PeakAnalysisDisplay = ({ data, unit }) => {
    if (!data || !data.top_peaks || data.top_peaks.length === 0) return <p>No peak data available.</p>;
    const chartData = {
      labels: data.top_peaks.map(p => new Date(p.timestamp).toLocaleString()),
      datasets: [{
          label: `Top ${data.top_peaks.length} Peaks (${unit})`,
          data: data.top_peaks.map(p => p.value),
          backgroundColor: 'rgba(0, 123, 255, 0.6)',
          borderColor: 'rgba(0, 123, 255, 1)',
          borderWidth: 1,
      }],
    };
    const chartOptions = { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, title: { display: true, text: `Peak Value (${unit})` } }, x: { title: { display: true, text: 'Timestamp' }}}, plugins: { legend: { display: true } } };
    const tableHeaders = [{key: 'timestamp', label: 'Timestamp'}, {key: 'value', label: `Value (${unit})`}];
    const renderRow = (item, key) => (<tr key={key}><td style={{ border: '1px solid #ddd', padding: '8px 10px' }}>{new Date(item.timestamp).toLocaleString()}</td><td style={{ border: '1px solid #ddd', padding: '8px 10px' }}>{item.value.toFixed(2)}</td></tr>);
    return (<div><h4>Peak Data Table</h4><Table headers={tableHeaders} data={data.top_peaks} renderRow={renderRow} caption={`Top ${data.top_peaks.length} Peaks`} keyPrefix="peak-row"/><h4>Peak Data Chart</h4><div style={{ height: '300px', marginBottom: '20px' }}><Bar data={chartData} options={chartOptions} /></div></div>);
};
const DurationCurveChart = ({ data, unit }) => {
    if (!data || !data.points || data.points.length === 0) return <p>No duration curve data available.</p>;
    const chartData = {
      labels: data.points.map(p => p.duration_hours),
      datasets: [{
          label: `Load Duration Curve (${unit})`,
          data: data.points.map(p => p.demand_value),
          borderColor: 'rgb(255, 99, 132)', backgroundColor: 'rgba(255, 99, 132, 0.5)', fill: false, tension: 0.1,
      }],
    };
    const chartOptions = { responsive: true, maintainAspectRatio: false, scales: { x: { title: { display: true, text: 'Duration (Hours)' }, type: 'linear' }, y: { title: { display: true, text: `Load (${unit})` }, beginAtZero: true }}, plugins: { legend: { display: true } } };
    return (<div style={{ height: '400px', marginBottom: '20px' }}><Line data={chartData} options={chartOptions} /></div>);
};
const SeasonalAnalysisCharts = ({ data, unit }) => {
    if (!data || !data.seasonal_profiles) return <p>No seasonal analysis data available.</p>;
    const seasons = Object.keys(data.seasonal_profiles);
    if (seasons.length === 0) return <p>No seasonal profiles found.</p>;
    const seasonColors = { winter: 'rgba(0, 123, 255, 0.8)', spring: 'rgba(40, 167, 69, 0.8)', summer: 'rgba(255, 193, 7, 0.8)', autumn: 'rgba(220, 53, 69, 0.8)', default: 'rgba(108, 117, 125, 0.8)' };
    return (<div>{seasons.map(season => {
        const profile = data.seasonal_profiles[season];
        if (!profile || profile.length === 0) return <p key={season}>No data for {season}.</p>;
        const chartData = {
          labels: profile.map(p => p.hour_of_day),
          datasets: [{
              label: `${season.charAt(0).toUpperCase() + season.slice(1)} Avg Profile (${unit})`,
              data: profile.map(p => p.average_demand),
              borderColor: seasonColors[season.toLowerCase()] || seasonColors.default,
              backgroundColor: (seasonColors[season.toLowerCase()] || seasonColors.default).replace('0.8', '0.5'),
              tension: 0.1, pointRadius: 2,
          }],
        };
        const chartOptions = { responsive: true, maintainAspectRatio: false, scales: { x: { title: { display: true, text: 'Hour of Day (0-23)' }, ticks: { stepSize: 1 } }, y: { title: { display: true, text: `Avg Load (${unit})` }, beginAtZero: true }}, plugins: { legend: { display: true }, title: {display: true, text: `${season.charAt(0).toUpperCase() + season.slice(1)} Profile`} } };
        return (<div key={season} style={{ height: '350px', marginBottom: '30px' }}><Line data={chartData} options={chartOptions} /></div>);
    })}</div>);
};
const ComprehensiveAnalysisDisplay = ({ data, unit }) => {
  if (!data) return <p>No comprehensive analysis data to display.</p>;
  const { basic_stats, load_factor_details, average_daily_profiles, average_weekly_profile, ramp_rates, missing_data_periods, data_resolution_minutes, data_period_start, data_period_end } = data;
  const commonChartOptions = { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, title: { display: true, text: `Load (${unit})` } } }, plugins: { legend: { display: true } } };
  const dailyProfileColors = { overall: 'rgba(54, 162, 235, 0.7)', weekday: 'rgba(75, 192, 192, 0.7)', weekend: 'rgba(255, 159, 64, 0.7)' };
  return (
    <div>
      <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>Overall Summary</h4>
      <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '10px', marginBottom: '15px'}}>
        <p><strong>Data Period:</strong><br/> {data_period_start ? new Date(data_period_start).toLocaleString() : 'N/A'} to {data_period_end ? new Date(data_period_end).toLocaleString() : 'N/A'}</p>
        <p><strong>Resolution:</strong><br/> {data_resolution_minutes?.toFixed(1)} minutes</p>
        {load_factor_details && <p><strong>Overall Load Factor:</strong><br/> {load_factor_details.overall_load_factor?.toFixed(3) || 'N/A'}</p>}
      </div>
      <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>Basic Statistics ({unit})</h4>
      {basic_stats ? (<Table headers={[{key: 'metric', label: 'Metric'}, {key: 'value', label: `Value (${unit})`}]} data={[{metric: 'Min Value', value: basic_stats.min_value?.toFixed(3)},{metric: 'Max Value', value: basic_stats.max_value?.toFixed(3)},{metric: 'Mean Value', value: basic_stats.mean_value?.toFixed(3)},{metric: 'Median Value', value: basic_stats.median_value?.toFixed(3)},{metric: 'Std Dev', value: basic_stats.std_dev?.toFixed(3)},{metric: 'Q1', value: basic_stats.q1_value?.toFixed(3)},{metric: 'Q3', value: basic_stats.q3_value?.toFixed(3)},{metric: 'Total Sum', value: basic_stats.total_sum?.toFixed(3)},{metric: 'Count', value: basic_stats.count},{metric: 'Duration (Hrs)', value: basic_stats.duration_hours?.toFixed(2)}]} renderRow={(item, key) => (<tr key={key}><td style={{ border: '1px solid #ddd', padding: '8px 10px', fontWeight:'500' }}>{item.metric}</td><td style={{ border: '1px solid #ddd', padding: '8px 10px' }}>{item.value}</td></tr>)} keyPrefix="comp-stats-row"/>) : <p>No basic stats.</p>}
      <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>Average Daily Profiles ({unit})</h4>
      {average_daily_profiles && Object.keys(average_daily_profiles).length > 0 ? (Object.keys(average_daily_profiles).map(key => { const pData = average_daily_profiles[key]; if (!pData || pData.length === 0) return <p key={key}>No {key} data.</p>; const cData = { labels: pData.map(p => p.hour_of_day), datasets: [{ label: `${key.charAt(0).toUpperCase() + key.slice(1)} Profile (${unit})`, data: pData.map(p => p.average_load), borderColor: dailyProfileColors[key.toLowerCase()] || 'grey', backgroundColor: (dailyProfileColors[key.toLowerCase()] || 'grey').replace('0.7','0.5'), tension: 0.1, pointRadius: 2 }]}; return (<div key={key} style={{height:'300px', marginBottom:'25px', border:'1px solid #eee', padding:'10px', borderRadius:'5px'}}><h5 style={{textAlign:'center', marginBottom:'10px'}}>{key.charAt(0).toUpperCase()+key.slice(1)}</h5><Line data={cData} options={{...commonChartOptions, scales: {...commonChartOptions.scales, x: {title:{display:true, text:'Hour of Day'}}}}}/></div>);})) : <p>No daily profiles.</p>}
      <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>Average Weekly Profile ({unit})</h4>
      {average_weekly_profile && average_weekly_profile.length > 0 ? (<div style={{height:'350px', marginBottom:'20px', border:'1px solid #eee', padding:'10px', borderRadius:'5px'}}><Bar data={{labels: average_weekly_profile.map(p=>p.day_of_week), datasets:[{label:`Avg Load by Day (${unit})`, data: average_weekly_profile.map(p=>p.average_load), backgroundColor:'rgba(255,99,132,0.6)', borderColor:'rgba(255,99,132,1)', borderWidth:1}]}} options={{...commonChartOptions, scales: {...commonChartOptions.scales, x: {title:{display:true, text:'Day of Week'}}}}}/></div>) : <p>No weekly profile.</p>}
      <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>Ramp Rates ({ramp_rates?.ramp_unit || unit + '/interval'})</h4>
      {ramp_rates ? (<div style={{border:'1px solid #eee', padding:'15px', borderRadius:'5px', marginBottom:'20px'}}><p><strong>Max Ramp Up:</strong> {ramp_rates.max_ramp_up_value?.toFixed(3)} (at {ramp_rates.max_ramp_up_timestamp ? new Date(ramp_rates.max_ramp_up_timestamp).toLocaleString() : 'N/A'})</p><p><strong>Max Ramp Down:</strong> {ramp_rates.max_ramp_down_value?.toFixed(3)} (at {ramp_rates.max_ramp_down_timestamp ? new Date(ramp_rates.max_ramp_down_timestamp).toLocaleString() : 'N/A'})</p><p><strong>Avg Abs Ramp Rate:</strong> {ramp_rates.average_ramp_rate_abs?.toFixed(3)}</p></div>) : <p>No ramp rates.</p>}
      <h4 style={{ marginTop: '20px', marginBottom: '10px' }}>Missing Data Periods</h4>
      {missing_data_periods && missing_data_periods.length > 0 ? (<Table headers={[{key:'start',label:'Start'},{key:'end',label:'End'},{key:'duration',label:'Duration (Hrs)'}]} data={missing_data_periods} renderRow={(item,key)=>(<tr key={key}><td style={{border:'1px solid #ddd',padding:'8px 10px'}}>{new Date(item.start_time).toLocaleString()}</td><td style={{border:'1px solid #ddd',padding:'8px 10px'}}>{new Date(item.end_time).toLocaleString()}</td><td style={{border:'1px solid #ddd',padding:'8px 10px',textAlign:'right'}}>{item.duration_hours.toFixed(2)}</td></tr>)} caption="Detected Missing Data Gaps" keyPrefix="missing-row"/>) : <p>No significant missing data.</p>}
    </div>
  );
};

// Profile Comparison Display Component
const ProfileComparisonDisplay = ({ data, unit }) => {
    if (!data) return <p>No profile comparison data to display.</p>;
    const { profiles_compared, summary_profile1, summary_profile2, comparative_metrics, time_series_data, correlation_coefficient, common_period_start, common_period_end, notes } = data;

    const commonChartOptions = { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: false, title: { display: true, text: `Load (${unit})` } }, x: { type: 'time', time: { tooltipFormat: 'MMM d, yyyy HH:mm' }, title: {display: true, text: 'Timestamp'}}}, plugins: { legend: { display: true } } };

    const timeSeriesChartData = time_series_data && time_series_data.length > 0 ? {
        datasets: [
            {
                label: `${profiles_compared[0]} (${unit})`,
                data: time_series_data.map(p => ({ x: new Date(p.timestamp), y: p.value_profile1 })),
                borderColor: 'rgba(0, 123, 255, 0.8)',
                backgroundColor: 'rgba(0, 123, 255, 0.5)',
                tension: 0.1,
                pointRadius: 1,
            },
            {
                label: `${profiles_compared[1]} (${unit})`,
                data: time_series_data.map(p => ({ x: new Date(p.timestamp), y: p.value_profile2 })),
                borderColor: 'rgba(255, 99, 132, 0.8)',
                backgroundColor: 'rgba(255, 99, 132, 0.5)',
                tension: 0.1,
                pointRadius: 1,
            }
        ]
    } : null;

    const differenceChartData = time_series_data && time_series_data.length > 0 ? {
        datasets: [
            {
                label: `Difference (${profiles_compared[0]} - ${profiles_compared[1]}) (${unit})`,
                data: time_series_data.map(p => ({ x: new Date(p.timestamp), y: p.difference })),
                borderColor: 'rgba(75, 192, 192, 0.8)',
                backgroundColor: 'rgba(75, 192, 192, 0.5)',
                tension: 0.1,
                pointRadius: 1,
            }
        ]
    } : null;


    return (
        <div>
            <h4>Comparison: {profiles_compared?.join(' vs ')}</h4>
            {notes && notes.length > 0 && <AlertMessage message={notes.join('; ')} type="info" />}
            <p><strong>Common Period:</strong> {common_period_start ? new Date(common_period_start).toLocaleString() : 'N/A'} to {common_period_end ? new Date(common_period_end).toLocaleString() : 'N/A'}</p>
            <p><strong>Correlation Coefficient (on common period):</strong> {correlation_coefficient?.toFixed(4) ?? 'N/A'}</p>

            <h5 style={{marginTop: '15px'}}>Comparative Metrics</h5>
            {comparative_metrics && comparative_metrics.length > 0 ? (
                 <Table
                    headers={[
                        {key: 'metric', label: 'Metric'},
                        {key: 'profile1', label: `${profiles_compared[0]} (${unit})`},
                        {key: 'profile2', label: `${profiles_compared[1]} (${unit})`},
                        {key: 'difference', label: `Difference (${unit})`},
                        {key: 'percent_diff', label: '% Difference'}
                    ]}
                    data={comparative_metrics}
                    renderRow={(item, key) => (
                        <tr key={key}>
                            <td style={{border:'1px solid #ddd', padding:'8px 10px', fontWeight:'500'}}>{item.metric_name}</td>
                            <td style={{border:'1px solid #ddd', padding:'8px 10px', textAlign:'right'}}>{typeof item.value_profile1 === 'number' ? item.value_profile1.toFixed(3) : item.value_profile1 || 'N/A'}</td>
                            <td style={{border:'1px solid #ddd', padding:'8px 10px', textAlign:'right'}}>{typeof item.value_profile2 === 'number' ? item.value_profile2.toFixed(3) : item.value_profile2 || 'N/A'}</td>
                            <td style={{border:'1px solid #ddd', padding:'8px 10px', textAlign:'right'}}>{item.difference?.toFixed(3) || 'N/A'}</td>
                            <td style={{border:'1px solid #ddd', padding:'8px 10px', textAlign:'right'}}>{item.percent_difference?.toFixed(2) || 'N/A'}%</td>
                        </tr>
                    )}
                    keyPrefix="comp-metric-row"
                 />
            ): <p>No comparative metrics available.</p>}

            {summary_profile1 && <Section title={`Summary for ${profiles_compared[0]} (Common Period)`} style={{backgroundColor: '#fff', marginTop:'15px'}}><PreFormatted data={summary_profile1} /></Section>}
            {summary_profile2 && <Section title={`Summary for ${profiles_compared[1]} (Common Period)`} style={{backgroundColor: '#fff', marginTop:'15px'}}><PreFormatted data={summary_profile2} /></Section>}

            {timeSeriesChartData && (
                <div style={{ height: '400px', marginTop: '20px', border: '1px solid #eee', padding: '10px', borderRadius: '5px' }}>
                    <h5 style={{textAlign: 'center', marginBottom: '10px'}}>Overlaid Time Series</h5>
                    <Line data={timeSeriesChartData} options={commonChartOptions} />
                </div>
            )}
            {differenceChartData && (
                 <div style={{ height: '300px', marginTop: '20px', border: '1px solid #eee', padding: '10px', borderRadius: '5px' }}>
                    <h5 style={{textAlign: 'center', marginBottom: '10px'}}>Time Series Difference</h5>
                    <Line data={differenceChartData} options={{...commonChartOptions, scales: {...commonChartOptions.scales, y: {...commonChartOptions.scales.y, title: {display:true, text: `Difference (${unit})`}}}}} />
                </div>
            )}
        </div>
    );
};


const LoadProfileAnalysis = () => {
  const [projectName, setProjectName] = useState("Default_Project");
  const [availableProfiles, setAvailableProfiles] = useState([]);
  const [selectedProfileId, setSelectedProfileId] = useState(''); // For individual analyses
  const [statisticalSummary, setStatisticalSummary] = useState(null);
  const [analysisUnit, setAnalysisUnit] = useState('kW'); // For statistical summary of single profile

  const [customAnalysisResult, setCustomAnalysisResult] = useState(null);

  const [analysisParams, setAnalysisParams] = useState({
    peak_analysis: { top_n_peaks: 5, unit: "kW" },
    duration_curve: { num_points: 100, unit: "kW" },
    seasonal_analysis: { aggregation_type: "average_daily_profile", unit: "kW" },
    comprehensive_analysis: { unit: "kW" },
    profile_comparison: { profileId1: '', profileId2: '', unit: 'kW'} // Added for comparison
  });

  const [loadingStates, setLoadingStates] = useState({ profiles: false, summary: false, peak: false, duration: false, seasonal: false, comprehensive: false, comparison: false });
  const [errorMessages, setErrorMessages] = useState({ profiles: null, summary: null, peak: null, duration: null, seasonal: null, comprehensive: null, comparison: null, general: null });
  const [actionMessage, setActionMessage] = useState({ text: '', type: 'info' });

  const updateLoading = (key, value) => setLoadingStates(prev => ({ ...prev, [key]: value }));
  const updateError = (key, value) => setErrorMessages(prev => ({ ...prev, [key]: value, general: value ? value : prev.general }));
  const showActionMessage = (text, type = 'info') => {
    setActionMessage({text, type});
    setTimeout(() => setActionMessage(prev => prev.text === text ? {text:'', type:'info'} : prev), 5000);
  };

  const fetchAvailableProfiles = useCallback(async () => {
    if (!projectName) {
        showActionMessage("Please enter a project name to load profiles.", "info");
        setAvailableProfiles([]);
        setSelectedProfileId('');
        setCustomAnalysisResult(null);
        setAnalysisParams(prev => ({ // Reset comparison profile IDs if project changes
            ...prev,
            profile_comparison: { ...prev.profile_comparison, profileId1: '', profileId2: ''}
        }));
        return;
    }
    updateLoading('profiles', true);
    updateError('profiles', null);
    updateError('general', null);
    try {
      const response = await api.listAvailableProfilesForAnalysis(projectName);
      setAvailableProfiles(response.data || []);
      if (response.data && response.data.length > 0) {
        // Auto-select first profile for individual analysis if none selected
        // if (!selectedProfileId) setSelectedProfileId(response.data[0].profile_id);
      } else {
        setSelectedProfileId(''); // Clear if no profiles
      }
      // Reset comparison profile IDs if the current selections are no longer in the new list
      const currentProfileIds = response.data?.map(p => p.profile_id) || [];
      setAnalysisParams(prev => {
        let newP1 = prev.profile_comparison.profileId1;
        let newP2 = prev.profile_comparison.profileId2;
        if (newP1 && !currentProfileIds.includes(newP1)) newP1 = '';
        if (newP2 && !currentProfileIds.includes(newP2)) newP2 = '';
        return {
          ...prev,
          profile_comparison: { ...prev.profile_comparison, profileId1: newP1, profileId2: newP2 }
        }
      });
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Failed to fetch available profiles";
      updateError('profiles', msg);
      showActionMessage(msg, "error");
      setAvailableProfiles([]);
      setSelectedProfileId('');
      setAnalysisParams(prev => ({
        ...prev,
        profile_comparison: { ...prev.profile_comparison, profileId1: '', profileId2: ''}
    }));
    } finally {
      updateLoading('profiles', false);
    }
  }, [projectName]);


  const fetchStatisticalSummary = useCallback(async () => {
    if (!projectName || !selectedProfileId) {
        setStatisticalSummary(null);
        return;
    }
    updateLoading('summary', true); updateError('summary', null); updateError('general', null);
    try {
      const response = await api.getStatisticalSummary(projectName, selectedProfileId, analysisUnit);
      setStatisticalSummary(response.data);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Failed to fetch statistical summary";
      updateError('summary', msg);
      showActionMessage(msg, "error");
      setStatisticalSummary(null);
    } finally {
      updateLoading('summary', false);
    }
  }, [projectName, selectedProfileId, analysisUnit]);

  useEffect(() => {
    if(selectedProfileId && projectName) fetchStatisticalSummary();
    else setStatisticalSummary(null);
  }, [selectedProfileId, analysisUnit, projectName, fetchStatisticalSummary]);

  const handleAnalysisParamChange = (analysisKey, paramName, value) => {
    setAnalysisParams(prev => ({
      ...prev,
      [analysisKey]: {
        ...prev[analysisKey],
        [paramName]: value
      }
    }));
  };

  // Handlers for individual analyses (Peak, Duration, Seasonal, Comprehensive)
  const runIndividualAnalysis = async (analysisType, apiFunction, paramsGetter, loadingKey, errorKey) => {
    if (!projectName || !selectedProfileId) {
        showActionMessage("Project name and a profile must be selected for this analysis.", "error");
        return;
    }
    updateLoading(loadingKey, true); updateError(errorKey, null); setCustomAnalysisResult(null);
    try {
      const params = paramsGetter();
      const response = await apiFunction(projectName, selectedProfileId, params);
      setCustomAnalysisResult({ type: analysisType, data: response.data, unit: params.unit });
      showActionMessage(`${analysisType} completed.`, "success");
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || `${analysisType} failed.`;
      updateError(errorKey, msg); showActionMessage(msg, "error");
    } finally { updateLoading(loadingKey, false); }
  };

  const handleRunPeakAnalysis = () => runIndividualAnalysis('Peak Analysis', api.performPeakAnalysis, () => analysisParams.peak_analysis, 'peak', 'peak');
  const handleRunDurationCurve = () => runIndividualAnalysis('Duration Curve', api.generateDurationCurve, () => analysisParams.duration_curve, 'duration', 'duration');
  const handleRunSeasonalAnalysis = () => runIndividualAnalysis('Seasonal Analysis', api.performSeasonalAnalysis, () => analysisParams.seasonal_analysis, 'seasonal', 'seasonal');
  const handleRunComprehensiveAnalysis = () => runIndividualAnalysis('Comprehensive Analysis', api.performComprehensiveAnalysis, () => analysisParams.comprehensive_analysis, 'comprehensive', 'comprehensive');

  const handleRunProfileComparison = async () => {
    if (!projectName || !analysisParams.profile_comparison.profileId1 || !analysisParams.profile_comparison.profileId2) {
        showActionMessage("Project name and two profiles must be selected for comparison.", "error");
        return;
    }
    if (analysisParams.profile_comparison.profileId1 === analysisParams.profile_comparison.profileId2) {
        showActionMessage("Please select two different profiles for comparison.", "error");
        return;
    }
    updateLoading('comparison', true); updateError('comparison', null); setCustomAnalysisResult(null);
    try {
      const { profileId1, profileId2, unit } = analysisParams.profile_comparison;
      const apiParams = { profile_ids: [profileId1, profileId2], unit: unit }; // Match backend model
      const response = await api.compareLoadProfiles(projectName, apiParams);
      setCustomAnalysisResult({type: 'Profile Comparison', data: response.data, unit: unit});
      showActionMessage("Profile comparison completed.", "success");
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || "Profile comparison failed.";
      updateError('comparison', msg); showActionMessage(msg, "error");
    } finally { updateLoading('comparison', false); }
  };

  return (
    <div style={{fontFamily: 'Arial, sans-serif', color: '#333', padding: '20px'}}>
      <h2 style={{color: '#0056b3', borderBottom: '2px solid #007bff', paddingBottom: '10px', marginBottom: '20px'}}>
        Load Profile Analysis: Project <Input type="text" value={projectName} onChange={e => {setProjectName(e.target.value); setAvailableProfiles([]); setSelectedProfileId(''); setCustomAnalysisResult(null);}} placeholder="Enter Project Name" style={{width: '200px', display:'inline-block', marginLeft:'10px'}} />
        <Button onClick={fetchAvailableProfiles} style={{marginLeft: '10px'}} disabled={!projectName || loadingStates.profiles}>
            {loadingStates.profiles ? 'Loading...' : 'Load Project Profiles'}
        </Button>
      </h2>

      <AlertMessage message={actionMessage.text} type={actionMessage.type} />
      {errorMessages.general && !Object.values(errorMessages).slice(0,-1).filter(Boolean).length && <AlertMessage message={errorMessages.general} type="error" /> }


      <Section title="1. Select Profile (for Individual Analysis)">
        {loadingStates.profiles && projectName && <p>Loading available profiles for '{projectName}'...</p>}
        <AlertMessage message={errorMessages.profiles} type="error" />
        {!loadingStates.profiles && availableProfiles.length === 0 && projectName && <p>No load profiles found for project '{projectName}'. Click "Load Project Profiles" or check project name.</p>}
        {!projectName && !loadingStates.profiles && <p>Enter a project name and click "Load Project Profiles".</p>}

        {availableProfiles.length > 0 && (
          <FormRow label="Choose Profile">
            <Select value={selectedProfileId} onChange={e => { setSelectedProfileId(e.target.value); setCustomAnalysisResult(null); }}>
              <option value="">-- Select a Profile --</option>
              {availableProfiles.map(p => (
                <option key={p.profile_id} value={p.profile_id}>
                  {p.profile_id} (Method: {p.method_used || 'N/A'})
                </option>
              ))}
            </Select>
          </FormRow>
        )}
      </Section>

      {selectedProfileId && projectName && (
        <>
          <Section title={`2. Statistical Summary for Profile: ${selectedProfileId}`}>
            <FormRow label="Display Unit">
                <Select value={analysisUnit} onChange={e => setAnalysisUnit(e.target.value)}>
                    <option value="kW">kW</option><option value="MW">MW</option><option value="GW">GW</option>
                </Select>
            </FormRow>
            {loadingStates.summary && <p>Loading statistical summary...</p>}
            <AlertMessage message={errorMessages.summary} type="error" />
            {statisticalSummary ? <PreFormatted data={statisticalSummary} /> : !loadingStates.summary && <p>No summary data to display. Select a profile and unit.</p>}
          </Section>

          <Section title="3. Perform Specific Analyses (on selected profile above)">
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px'}}>
              {/* Peak Analysis Form */}
              <div style={{padding: '15px', border:'1px solid #ccc', borderRadius: '5px', backgroundColor:'#fff', display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
                <div>
                  <h4>Peak Analysis</h4>
                <FormRow label="Top N Peaks">
                  <Input type="number" value={analysisParams.peak_analysis.top_n_peaks}
                         onChange={e => handleAnalysisParamChange('peak_analysis', 'top_n_peaks', parseInt(e.target.value) || 1)} min="1"/>
                </FormRow>
                <FormRow label="Unit">
                  <Select value={analysisParams.peak_analysis.unit} onChange={e => handleAnalysisParamChange('peak_analysis', 'unit', e.target.value)}>
                      <option value="kW">kW</option><option value="MW">MW</option><option value="GW">GW</option>
                  </Select>
                </FormRow>
               </div>
                <Button onClick={handleRunPeakAnalysis} disabled={loadingStates.peak || !selectedProfileId} style={{width:'100%', marginTop:'10px'}} title={!selectedProfileId ? "Select a profile first" : ""}>
                  {loadingStates.peak ? 'Running...' : 'Run Peak Analysis'}
                </Button>
                <AlertMessage message={errorMessages.peak} type="error" />
               </div>

              {/* Duration Curve Form */}
              <div style={{padding: '15px', border:'1px solid #ccc', borderRadius: '5px', backgroundColor:'#fff', display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
                <div>
                  <h4>Load Duration Curve</h4>
                <FormRow label="Number of Points">
                  <Input type="number" value={analysisParams.duration_curve.num_points}
                         onChange={e => handleAnalysisParamChange('duration_curve', 'num_points', parseInt(e.target.value) || 10)} min="10" />
                </FormRow>
                <FormRow label="Unit">
                   <Select value={analysisParams.duration_curve.unit} onChange={e => handleAnalysisParamChange('duration_curve', 'unit', e.target.value)}>
                      <option value="kW">kW</option><option value="MW">MW</option><option value="GW">GW</option>
                  </Select>
                </FormRow>
               </div>
                <Button onClick={handleRunDurationCurve} disabled={loadingStates.duration || !selectedProfileId} style={{width:'100%', marginTop:'10px'}} title={!selectedProfileId ? "Select a profile first" : ""}>
                  {loadingStates.duration ? 'Generating...' : 'Generate Duration Curve'}
                </Button>
                <AlertMessage message={errorMessages.duration} type="error" />
               </div>

              {/* Seasonal Analysis Form */}
              <div style={{padding: '15px', border:'1px solid #ccc', borderRadius: '5px', backgroundColor:'#fff', display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
                <div>
                  <h4>Seasonal Analysis</h4>
                <FormRow label="Aggregation Type">
                  <Select value={analysisParams.seasonal_analysis.aggregation_type}
                          onChange={e => handleAnalysisParamChange('seasonal_analysis', 'aggregation_type', e.target.value)}>
                    <option value="average_daily_profile">Average Daily Profile</option>
                  </Select>
                </FormRow>
                 <FormRow label="Unit">
                   <Select value={analysisParams.seasonal_analysis.unit} onChange={e => handleAnalysisParamChange('seasonal_analysis', 'unit', e.target.value)}>
                      <option value="kW">kW</option><option value="MW">MW</option><option value="GW">GW</option>
                  </Select>
                </FormRow>
                </div>
                <Button onClick={handleRunSeasonalAnalysis} disabled={loadingStates.seasonal || !selectedProfileId} style={{width:'100%', marginTop:'10px'}} title={!selectedProfileId ? "Select a profile first" : ""}>
                  {loadingStates.seasonal ? 'Running...' : 'Run Seasonal Analysis'}
                </Button>
                <AlertMessage message={errorMessages.seasonal} type="error" />
              </div>

              {/* Comprehensive Analysis Form */}
              <div style={{padding: '15px', border:'1px solid #ccc', borderRadius: '5px', backgroundColor:'#fff', display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
                <div>
                  <h4>Comprehensive Analysis</h4>
                  <FormRow label="Unit">
                    <Select value={analysisParams.comprehensive_analysis.unit} onChange={e => handleAnalysisParamChange('comprehensive_analysis', 'unit', e.target.value)}>
                        <option value="kW">kW</option><option value="MW">MW</option><option value="GW">GW</option>
                    </Select>
                  </FormRow>
                </div>
                <Button onClick={handleRunComprehensiveAnalysis} disabled={loadingStates.comprehensive || !selectedProfileId} style={{width:'100%', marginTop:'10px'}} title={!selectedProfileId ? "Select a profile first" : ""}>
                  {loadingStates.comprehensive ? 'Running...' : 'Run Comprehensive Analysis'}
                </Button>
                <AlertMessage message={errorMessages.comprehensive} type="error" />
              </div>
            </div>
          </Section>

          {/* Results for Individual Analysis */}
          {customAnalysisResult && customAnalysisResult.type !== 'Profile Comparison' && (
            <Section title={`4. Result for: ${customAnalysisResult.type} (Profile: ${selectedProfileId})`}>
              {customAnalysisResult.type === 'Peak Analysis' && <PeakAnalysisDisplay data={customAnalysisResult.data} unit={customAnalysisResult.unit} />}
              {customAnalysisResult.type === 'Duration Curve' && <DurationCurveChart data={customAnalysisResult.data} unit={customAnalysisResult.unit}/>}
              {customAnalysisResult.type === 'Seasonal Analysis' && <SeasonalAnalysisCharts data={customAnalysisResult.data} unit={customAnalysisResult.unit}/>}
              {customAnalysisResult.type === 'Comprehensive Analysis' && <ComprehensiveAnalysisDisplay data={customAnalysisResult.data} unit={customAnalysisResult.unit} />}

              {!(customAnalysisResult.type === 'Peak Analysis' || customAnalysisResult.type === 'Duration Curve' || customAnalysisResult.type === 'Seasonal Analysis' || customAnalysisResult.type === 'Comprehensive Analysis') &&
                <PreFormatted data={customAnalysisResult.data} />
              }
            </Section>
          )}
        </>
      )}

      {/* Section for Profile Comparison - always visible if project is loaded and has enough profiles */}
      {projectName && availableProfiles.length >= 1 && ( // Show if project loaded, even if only 1 profile (to show selectors)
        <Section title="4. Compare Two Profiles">
           <div style={{padding: '15px', border:'1px solid #ccc', borderRadius: '5px', backgroundColor:'#fff', marginBottom: '20px'}}>
            <FormRow label="Profile 1">
              <Select
                value={analysisParams.profile_comparison.profileId1}
                onChange={e => handleAnalysisParamChange('profile_comparison', 'profileId1', e.target.value)}
                disabled={availableProfiles.length === 0}
              >
                <option value="">-- Select Profile 1 --</option>
                {availableProfiles.map(p => (
                  <option key={`comp-p1-${p.profile_id}`} value={p.profile_id} disabled={p.profile_id === analysisParams.profile_comparison.profileId2}>
                    {p.profile_id}
                  </option>
                ))}
              </Select>
            </FormRow>
            <FormRow label="Profile 2">
              <Select
                value={analysisParams.profile_comparison.profileId2}
                onChange={e => handleAnalysisParamChange('profile_comparison', 'profileId2', e.target.value)}
                disabled={availableProfiles.length === 0}
              >
                <option value="">-- Select Profile 2 --</option>
                {availableProfiles.map(p => (
                  <option key={`comp-p2-${p.profile_id}`} value={p.profile_id} disabled={p.profile_id === analysisParams.profile_comparison.profileId1}>
                    {p.profile_id}
                  </option>
                ))}
              </Select>
            </FormRow>
            <FormRow label="Comparison Unit">
              <Select value={analysisParams.profile_comparison.unit} onChange={e => handleAnalysisParamChange('profile_comparison', 'unit', e.target.value)}>
                  <option value="kW">kW</option><option value="MW">MW</option><option value="GW">GW</option>
              </Select>
            </FormRow>
            <Button
                onClick={handleRunProfileComparison}
                disabled={loadingStates.comparison || !analysisParams.profile_comparison.profileId1 || !analysisParams.profile_comparison.profileId2 || analysisParams.profile_comparison.profileId1 === analysisParams.profile_comparison.profileId2 || availableProfiles.length < 2}
                style={{width:'100%', marginTop:'10px'}}
                title={
                    availableProfiles.length < 2 ? "Need at least two profiles in the project to compare" :
                    (!analysisParams.profile_comparison.profileId1 || !analysisParams.profile_comparison.profileId2 ? "Select two profiles" :
                    (analysisParams.profile_comparison.profileId1 === analysisParams.profile_comparison.profileId2 ? "Select two different profiles" : "Run Comparison"))
                }
            >
              {loadingStates.comparison ? 'Comparing...' : 'Run Profile Comparison'}
            </Button>
            <AlertMessage message={errorMessages.comparison} type="error" />
          </div>

          {/* Results for Profile Comparison */}
          {customAnalysisResult && customAnalysisResult.type === 'Profile Comparison' && (
             <Section title={`Result for: ${customAnalysisResult.type}`}>
                <ProfileComparisonDisplay data={customAnalysisResult.data} unit={customAnalysisResult.unit} />
             </Section>
          )}
        </Section>
      )}
    </div>
  );
};

export default LoadProfileAnalysis;
