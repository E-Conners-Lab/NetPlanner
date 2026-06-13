import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        // Backend origin. Defaults to the local dev backend; override with
        // VITE_API_PROXY (e.g. E2E runs the backend on a non-default port).
        target: process.env.VITE_API_PROXY || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        // vite 8's bundler (rolldown) requires manualChunks as a FUNCTION;
        // the old object form throws "manualChunks is not a function".
        // Same split as before: React core in one vendor chunk, the heavy
        // recharts/d3 graph in another.
        manualChunks(id) {
          if (!id.includes('node_modules')) return;
          if (id.includes('recharts') || /[\\/]d3-|[\\/]victory-vendor[\\/]/.test(id)) {
            return 'vendor-recharts';
          }
          if (/[\\/]node_modules[\\/](react|react-dom|react-router|react-router-dom|scheduler)[\\/]/.test(id)) {
            return 'vendor-react';
          }
        },
      },
    },
  },
});
