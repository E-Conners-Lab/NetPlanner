import axios from 'axios';

/**
 * Shared Axios instance for all NetPlanner API calls.
 * Base URL resolves from the Vite env variable at build time, falling
 * back to '/api' so the Vite dev-server proxy and the Nginx proxy_pass
 * both work without additional config.
 */
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30_000,
});

/* ── Request interceptor ────────────────────────────────────── */
client.interceptors.request.use(
  (config) => {
    // Future: attach auth token here
    // const token = getToken();
    // if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  },
  (error) => Promise.reject(error)
);

/* ── Response interceptor ───────────────────────────────────── */
client.interceptors.response.use(
  (response) => response,
  (error) => {
    // Future: handle 401 → redirect to login, 403 → show permission error
    return Promise.reject(error);
  }
);

export default client;
