import React from 'react';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';
import Layout from './components/common/Layout';
import Navigation from './components/common/Navigation'; // Added Navigation
import ErrorBoundary from './components/common/ErrorBoundary';

// Import Pages (Lazy loading can be implemented later for optimization)
import Dashboard from './pages/Dashboard';
import ProjectManagement from './pages/ProjectManagement';
import DemandProjection from './pages/DemandProjection';
import DemandVisualization from './pages/DemandVisualization';
import LoadProfile from './pages/LoadProfile';
import LoadProfileAnalysis from './pages/LoadProfileAnalysis';
import PyPSAModeling from './pages/PyPSAModeling';
import Admin from './pages/Admin';

// Import global styles
import './styles/globals.css';
// Import other specific styles if needed globally (e.g., for a UI library)
// import './styles/components.css'; // If some component styles are globally relevant
// import './styles/charts.css'; // If chart styles are globally relevant

function App() {
  return (
    <Router>
      <ErrorBoundary>
        <Layout>
          <Navigation /> {/* Include Navigation within Layout */}
          <div className="container"> {/* Optional: for consistent padding/max-width */}
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/projects" element={<ProjectManagement />} />
              <Route path="/demand-projection" element={<DemandProjection />} />
              <Route path="/demand-visualization" element={<DemandVisualization />} />
              <Route path="/load-profile" element={<LoadProfile />} />
              <Route path="/load-profile-analysis" element={<LoadProfileAnalysis />} />
              <Route path="/pypsa-modeling" element={<PyPSAModeling />} />
              <Route path="/admin" element={<Admin />} />
              {/* Add more routes as needed */}
            </Routes>
          </div>
        </Layout>
      </ErrorBoundary>
    </Router>
  );
}

export default App;
