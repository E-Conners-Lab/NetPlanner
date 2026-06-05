import client from './client.js';
import { readCsrfToken } from './csrf.js';

/**
 * Auth API — the SPA never sees the JWT. The backend issues an httpOnly
 * cookie on /auth/login and /auth/register; we just call the routes and
 * read /auth/me to learn who the cookie identifies.
 */

/**
 * Make sure a CSRF token cookie exists before a mutating auth call (SEC-07).
 * The /auth/me probe on boot normally seeds it, but a user landing straight
 * on /login may submit before that resolves — this closes the race.
 */
async function ensureCsrfToken() {
  if (readCsrfToken()) return;
  try {
    await client.get('/auth/csrf');
  } catch {
    // Non-fatal — the login request below will surface any real failure.
  }
}

export async function register({ email, password }) {
  await ensureCsrfToken();
  const res = await client.post('/auth/register', { email, password });
  return res.data;
}

export async function login({ email, password }) {
  await ensureCsrfToken();
  const res = await client.post('/auth/login', { email, password });
  return res.data;
}

export async function logout() {
  await client.post('/auth/logout');
}

export async function fetchCurrentUser() {
  const res = await client.get('/auth/me');
  return res.data;
}
