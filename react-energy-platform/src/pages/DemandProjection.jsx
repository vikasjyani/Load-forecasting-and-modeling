import React, { useState, useEffect, useCallback } from 'react';
import api from '../services/api'; // Assuming api.js is correctly set up

// Basic styled components for layout (can be moved to a separate file)
const Section = ({ title, children }) => (
  <section style={{ marginBottom: '20px', padding: '15px', border: '1px solid #eee' }}>
    <h3>{title}</h3>
    {children}
  </section>
);

const PreFormatted = ({ data }) => <pre>{JSON.stringify(data, null, 2)}</pre>;

const DemandProjection = () => {
  const [projectName, setProjectName] = useState("Default_Project"); // Hardcoded for now
  const [inputSummary, setInputSummary] = useState(null);
  const [selectedSector, setSelectedSector] = useState('');
  const [sectorDetails, setSectorDetails] = useState(null);
  const [independentVars, setIndependentVars] = useState(null);
  const [correlationData, setCorrelationData] = useState(null);

  const [forecastJobId, setForecastJobId] = useState(null);
  const [forecastStatus, setForecastStatus] = useState(null);
  const [forecastResult, setForecastResult] = useState(null);

  const [loadingSummary, setLoadingSummary] = useState(false);
  const [loadingSector, setLoadingSector] = useState(false);
  const [error, setError] = useState(null);
  const [jobError, setJobError] = useState(null);


  // Fetch input data summary on component mount or when projectName changes
  useEffect(() => {
    if (!projectName) return;
    const fetchSummary = async () => {
      setLoadingSummary(true);
      setError(null);
      try {
        const response = await api.getProjectInputDataSummary(projectName);
        setInputSummary(response.data);
        if (response.data?.sectors_available?.length > 0) {
          setSelectedSector(response.data.sectors_available[0]); // Auto-select first sector
        }
      } catch (err) {
        console.error("Error fetching input summary:", err);
        setError(err.response?.data?.detail || err.message || 'Failed to fetch input summary');
        setInputSummary(null);
      } finally {
        setLoadingSummary(false);
      }
    };
    fetchSummary();
  }, [projectName]);

  // Fetch sector-specific details when selectedSector changes
  useEffect(() => {
    if (!projectName || !selectedSector) {
      setSectorDetails(null);
      setIndependentVars(null);
      setCorrelationData(null);
      return;
    }

    const fetchSectorDetails = async () => {
      setLoadingSector(true);
      setError(null); // Clear general error
      try {
        // const detailsRes = await api.getSectorData(projectName, selectedSector);
        // setSectorDetails(detailsRes.data); // Potentially large, skip for now for brevity

        const indVarsRes = await api.getIndependentVariables(projectName, selectedSector);
        setIndependentVars(indVarsRes.data);

        const corrRes = await api.getCorrelationData(projectName, selectedSector);
        setCorrelationData(corrRes.data);

      } catch (err) {
        console.error(`Error fetching data for sector ${selectedSector}:`, err);
        setError(err.response?.data?.detail || err.message || `Failed to fetch data for ${selectedSector}`);
      } finally {
        setLoadingSector(false);
      }
    };
    fetchSectorDetails();
  }, [projectName, selectedSector]);

  // Poll for forecast status if a job is running
  useEffect(() => {
    let intervalId;
    if (forecastJobId && (!forecastStatus ||
        (forecastStatus.status !== 'COMPLETED' && forecastStatus.status !== 'FAILED' && forecastStatus.status !== 'CANCELLED'))) {
      intervalId = setInterval(async () => {
        try {
          setJobError(null);
          const response = await api.getForecastStatus(forecastJobId);
          setForecastStatus(response.data);
          if (response.data.status === 'COMPLETED' || response.data.status === 'FAILED' || response.data.status === 'CANCELLED') {
            setForecastResult(response.data.result_summary || response.data.error || "Job finished.");
            clearInterval(intervalId);
          }
        } catch (err) {
          console.error("Error fetching forecast status:", err);
          setJobError(err.response?.data?.detail || err.message || "Error fetching job status.");
          // Optionally stop polling on repeated errors, or if job not found (404)
          if(err.response?.status === 404) clearInterval(intervalId);
        }
      }, 5000); // Poll every 5 seconds
    }
    return () => clearInterval(intervalId); // Cleanup on unmount or if job ID changes
  }, [forecastJobId, forecastStatus]);


  const handleRunForecast = async () => {
    if (!inputSummary || !inputSummary.sectors_available || inputSummary.sectors_available.length === 0) {
      alert("No sectors available to forecast.");
      return;
    }
    setJobError(null);
    setForecastStatus(null);
    setForecastResult(null);

    // Simplified config for testing
    const targetSector = inputSummary.sectors_available[0]; // Forecast only the first available sector
    const defaultConfig = {
      scenarioName: `TestScenario_${new Date().toISOString().replace(/[-:.]/g, "").slice(0,14)}`,
      targetYear: 2030,
      excludeCovidYears: true,
      sectorConfigs: {
        [targetSector]: { // Use dynamic key for the selected sector
          models: ["MLR", "WAM"], // Example models
          independentVars: independentVars?.suitable_variables?.slice(0,2) || [], // Use first two suitable vars
          windowSize: 10
        }
      },
      detailedConfiguration: {
          // global settings if any
      }
    };

    try {
      const response = await api.runForecast(projectName, defaultConfig);
      setForecastJobId(response.data.job_id);
      setForecastStatus({ status: 'STARTING', message: 'Forecast job initiated...' }); // Initial status
    } catch (err) {
      console.error("Error running forecast:", err);
      setJobError(err.response?.data?.detail || err.message || "Failed to start forecast job.");
      setForecastJobId(null);
    }
  };

  const handleSectorChange = (event) => {
    setSelectedSector(event.target.value);
  };

  return (
    <div>
      <h2>Demand Projection for Project: {projectName}</h2>
      {error && <div style={{color: 'red'}}><PreFormatted data={{ error }} /></div>}

      <Section title="Input Data Summary">
        {loadingSummary ? <p>Loading summary...</p> : <PreFormatted data={inputSummary} />}
      </Section>

      {inputSummary && inputSummary.sectors_available && (
        <Section title="Sector Analysis">
          <label htmlFor="sector-select">Select Sector: </label>
          <select id="sector-select" value={selectedSector} onChange={handleSectorChange}>
            {inputSummary.sectors_available.map(sector => (
              <option key={sector} value={sector}>{sector}</option>
            ))}
          </select>
          {loadingSector && <p>Loading sector data...</p>}
          {selectedSector && (
            <>
              <h4>Independent Variables for {selectedSector}</h4>
              <PreFormatted data={independentVars} />
              <h4>Correlation Data for {selectedSector}</h4>
              <PreFormatted data={correlationData} />
            </>
          )}
        </Section>
      )}

      <Section title="Run Forecast">
        <button onClick={handleRunForecast} disabled={!inputSummary || loadingSummary || loadingSector || (forecastJobId && forecastStatus?.status === 'RUNNING')}>
          Run Default Forecast (for {selectedSector || 'first available sector'})
        </button>
        {forecastJobId && <p>Forecast Job ID: {forecastJobId}</p>}
        {jobError && <div style={{color: 'red'}}><PreFormatted data={{ jobError }} /></div>}
        <h4>Forecast Status</h4>
        <PreFormatted data={forecastStatus} />
        <h4>Forecast Result/Error</h4>
        <PreFormatted data={forecastResult} />
      </Section>

      {/* Placeholder for actual ForecastConfigForm and TimeSeriesChart */}
      {/* <ForecastConfigForm onSubmit={handleConfigSubmit} /> */}
      {/* {loading && <p>Loading projection...</p>}
      {error && <p>Error: {error.message}</p>}
      {projection && <TimeSeriesChart data={projection} />} */}
    </div>
  );
};

export default DemandProjection;
