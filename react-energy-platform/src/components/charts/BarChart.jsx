import React from 'react';
// Placeholder for a chart library

const BarChart = ({ data, options }) => {
  return (
    <div>
      <h3>Bar Chart</h3>
      <pre>{JSON.stringify(data, null, 2)}</pre>
      {/* Chart rendering logic */}
    </div>
  );
};

export default BarChart;
