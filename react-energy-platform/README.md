# React Energy Platform Frontend

This directory contains the frontend application for the Energy Platform, built with React (using Vite as the build tool).

## Project Structure

```
react-energy-platform/
├── public/
│   ├── index.html             # Main HTML template
│   └── favicon.ico            # Favicon
│   └── ...                    # Other static assets
├── src/
│   ├── components/            # Reusable UI components
│   │   ├── common/            # General purpose components (Layout, Nav, etc.)
│   │   ├── charts/            # Chart components
│   │   └── forms/             # Form components
│   │
│   ├── pages/                 # Page-level components (routed)
│   │   ├── Dashboard.jsx
│   │   └── ...
│   │
│   ├── hooks/                 # Custom React hooks
│   │   ├── useApi.js
│   │   └── ...
│   │
│   ├── services/              # API service integrations
│   │   ├── api.js             # Base API client (e.g., Axios instance)
│   │   └── ...                # Specific service modules (projectService.js)
│   │
│   ├── store/                 # State management (e.g., Redux Toolkit)
│   │   ├── index.js           # Store configuration
│   │   ├── slices/            # Redux slices
│   │   └── middleware/        # Custom middleware
│   │
│   ├── utils/                 # Utility functions (constants, formatters, etc.)
│   │
│   ├── styles/                # CSS files (global, components, etc.)
│   │   ├── globals.css
│   │   └── ...
│   │
│   ├── App.jsx                # Main application component with routing
│   ├── index.js               # Entry point, renders App
│   └── setupTests.js          # Jest setup for tests
│
├── package.json               # Project dependencies and scripts
├── tailwind.config.js         # Tailwind CSS configuration (if used)
├── vite.config.js             # Vite configuration
└── README.md                  # This file
```

## Setup and Running

### Prerequisites
- Node.js (v16+ recommended)
- npm or yarn

### Installation

1.  **Navigate to the `react-energy-platform` directory.**
2.  **Install dependencies:**
    Using npm:
    ```bash
    npm install
    ```
    Or using yarn:
    ```bash
    yarn install
    ```

### Running the Development Server

1.  **Start the Vite dev server:**
    Using npm:
    ```bash
    npm run dev
    ```
    Or (if you have a start script for Vite):
    ```bash
    npm start
    ```
    Using yarn:
    ```bash
    yarn dev
    ```
    The application will typically be available at `http://localhost:3000` (or as configured in `vite.config.js`). The server supports Hot Module Replacement (HMR).

### Building for Production

1.  **Create a production build:**
    Using npm:
    ```bash
    npm run build
    ```
    Using yarn:
    ```bash
    yarn build
    ```
    This will generate optimized static assets in the `build` (or `dist`, depending on `vite.config.js`) directory.

### Previewing the Production Build

After building, you can preview the production app locally:
Using npm:
```bash
npm run serve
```
Using yarn:
```bash
yarn serve
```

## Key Technologies

-   **React**: JavaScript library for building user interfaces.
-   **Vite**: Next-generation frontend tooling (dev server, bundler).
-   **React Router**: For client-side routing.
-   **Redux Toolkit**: (Optional, if implemented) For state management.
-   **Axios**: For making HTTP requests to the backend API.
-   **Tailwind CSS**: (Optional, if implemented) A utility-first CSS framework.
-   **Jest & React Testing Library**: For testing components and logic.

## Environment Variables

Create a `.env` file in the root of the `react-energy-platform` directory to manage environment-specific variables. Vite uses a specific prefix for environment variables to be exposed to the client: `VITE_`.

Example `.env` file:
```
VITE_APP_NAME="Energy Platform"
VITE_API_BASE_URL="http://localhost:8000/api/v1"
```
Access these in your code using `import.meta.env.VITE_VARIABLE_NAME`.

**Note:** For variables used by Create React App (if migrating or using `react-scripts`), the prefix is `REACT_APP_`. Adjust your `package.json` scripts and variable access accordingly if not using Vite.

## Linting and Formatting

Consider setting up ESLint and Prettier for code quality and consistency. Configuration files (e.g., `.eslintrc.js`, `.prettierrc.js`) would be in the root of this directory.

## Testing

Tests are typically located alongside the files they test (e.g., `MyComponent.test.js`) or in `__tests__` subdirectories.

Run tests using:
Using npm:
```bash
npm test
```
Using yarn:
```bash
yarn test
```
This will launch the Jest test runner in watch mode.
The `src/setupTests.js` file is used for global test setup.
```

## Deployment
The production build (from `npm run build` or `yarn build`) can be deployed to any static hosting service (e.g., Netlify, Vercel, AWS S3, GitHub Pages) or served via a Node.js server.
Make sure your backend API is accessible from where the frontend is hosted.
