import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000, // You can specify the port for the dev server
    proxy: {
      // Proxy API requests to the backend during development
      // Example: '/api/v1' requests will be forwarded to 'http://localhost:8000/api/v1'
      '/api': {
        target: 'http://localhost:8000', // Your FastAPI backend URL
        changeOrigin: true,
        // rewrite: (path) => path.replace(/^\/api/, ''), // if you need to remove /api prefix
      },
    },
  },
  build: {
    outDir: 'build', // Output directory for production build (CRA default is 'build')
    sourcemap: true, // Generate source maps for production
  },
  // resolve: {
  //   alias: {
  //     // Example: Setup aliases for easier imports
  //     // '@components': path.resolve(__dirname, 'src/components'),
  //     // '@services': path.resolve(__dirname, 'src/services'),
  //   },
  // },
});
