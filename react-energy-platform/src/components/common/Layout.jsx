import React from 'react';

const Layout = ({ children }) => {
  return (
    <div>
      <header>
        {/* Navigation component will go here */}
        <h1>Energy Platform</h1>
      </header>
      <main>{children}</main>
      <footer>
        <p>&copy; 2023 Energy Corp</p>
      </footer>
    </div>
  );
};

export default Layout;
