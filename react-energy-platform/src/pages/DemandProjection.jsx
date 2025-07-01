import React from 'react';
// import ForecastConfigForm from '../components/forms/ForecastConfigForm';
// import TimeSeriesChart from '../components/charts/TimeSeriesChart';
// import useForecast from '../hooks/useForecast';

const DemandProjection = () => {
  // const { projection, loading, error, getProjection } = useForecast();

  // const handleConfigSubmit = (config) => {
  //   getProjection(config);
  // };

  return (
    <div>
      <h2>Demand Projection</h2>
      {/* <ForecastConfigForm onSubmit={handleConfigSubmit} /> */}
      {/* {loading && <p>Loading projection...</p>}
      {error && <p>Error: {error.message}</p>}
      {projection && <TimeSeriesChart data={projection} />} */}
      <p>View and configure demand projections.</p>
    </div>
  );
};

export default DemandProjection;
