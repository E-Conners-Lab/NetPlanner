import axios from 'axios';
import { CSRF_HEADER, readCsrfToken } from './csrf.js';

/**
 * Shared Axios instance for all NetPlanner API calls.
 *
 * Cookies (session auth) ride along on every request because
 * `withCredentials` is true — the BFF pattern keeps the JWT in an httpOnly
 * cookie the SPA never touches. On a 401 we broadcast `auth:unauthorized`
 * so route guards can redirect to /login without coupling every API caller.
 */
const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
  timeout: 30_000,
});

const UNSAFE_METHODS = new Set(['post', 'put', 'patch', 'delete']);

/* ── Request interceptor: attach the CSRF token (SEC-07) ─────── */
client.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase();
  if (UNSAFE_METHODS.has(method)) {
    const token = readCsrfToken();
    if (token) {
      config.headers = config.headers || {};
      config.headers[CSRF_HEADER] = token;
    }
  }
  return config;
});

/* ── Response interceptor ───────────────────────────────────── */
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      // Surface a single global signal so route guards can react. Multiple
      // listeners (App.jsx, ProtectedRoute) handle the redirect.
      try {
        window.dispatchEvent(new CustomEvent('auth:unauthorized'));
      } catch {
        // ignore — non-browser env (SSR/tests)
      }
    }
    return Promise.reject(error);
  }
);

export default client;
