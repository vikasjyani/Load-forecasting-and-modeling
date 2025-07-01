import React, { useState } from 'react';

const ForecastConfigForm = ({ onSubmit, initialData = {} }) => {
  const [model, setModel] = useState(initialData.model || 'default_model');
  const [horizon, setHorizon] = useState(initialData.horizon || 24);

  const handleSubmit = (event) => {
    event.preventDefault();
    onSubmit({ model, horizon });
  };

  return (
    <form onSubmit={handleSubmit}>
      <div>
        <label htmlFor="forecastModel">Model:</label>
        <input
          type="text"
          id="forecastModel"
          value={model}
          onChange={(e) => setModel(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="forecastHorizon">Horizon (hours):</label>
        <input
          type="number"
          id="forecastHorizon"
          value={horizon}
          onChange={(e) => setHorizon(parseInt(e.target.value, 10))}
        />
      </div>
      <button type="submit">Configure Forecast</button>
    </form>
  );
};

export default ForecastConfigForm;
