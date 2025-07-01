import React from 'react';
import { Link } from 'react-router-dom'; // Assuming use of React Router

const Navigation = () => {
  return (
    <nav>
      <ul>
        <li><Link to="/">Dashboard</Link></li>
        <li><Link to="/projects">Projects</Link></li>
        {/* Add other navigation links here */}
      </ul>
    </nav>
  );
};

export default Navigation;
