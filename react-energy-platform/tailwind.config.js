/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}", // Scan all JS/JSX/TS/TSX files in src
    "./public/index.html",      // Scan main HTML file
  ],
  theme: {
    extend: {
      colors: {
        primary: '#007bff', // Example primary color
        secondary: '#6c757d', // Example secondary color
        // Add custom colors here
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'], // Example custom font
        // Add custom font families here
      },
      // You can extend other Tailwind utilities like spacing, screens, etc.
    },
  },
  plugins: [
    // require('@tailwindcss/forms'), // Example plugin for form styling
    // Add other Tailwind plugins here
  ],
};
