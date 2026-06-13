import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E configuration for the NetPlanner frontend.
 *
 * These tests drive the REAL UI against a REAL backend so we catch runtime
 * regressions the CI build-only "Frontend gate" cannot — every button and the
 * intended user flow. The dependency-upgrade work (React 19, react-router 7,
 * react-markdown 10, vite) is gated on this suite staying green.
 *
 * `webServer` boots the full stack for the run:
 *   - backend : FastAPI on :8000, pointed at an EPHEMERAL SQLite file so a run
 *     never touches dev data. In development mode the app's `init_db` creates
 *     the schema directly (no alembic step needed).
 *   - frontend: the Vite dev server on :5173, which proxies `/api` to :8000.
 *
 * The Advisor page makes real LLM calls — those are STUBBED at the network
 * layer inside the relevant spec (AI-3/AI-4: never hit a paid model in tests).
 */

// Non-default ports so the E2E stack never collides with a local dev server
// (or an unrelated project/container) already bound to :5173 / :8000.
const FRONTEND_PORT = 5273;
const BACKEND_PORT = 8137;
// Pin to 127.0.0.1 (not "localhost") everywhere: uvicorn binds IPv4 and on
// macOS "localhost" can resolve to ::1 first, which never connects.
const HOST = '127.0.0.1';
const BASE_URL = `http://${HOST}:${FRONTEND_PORT}`;

// Ephemeral DB + non-secure cookies so the session cookie works over plain
// HTTP in the test browser. JWT_SECRET is a throwaway — never a real secret.
const backendEnv = {
  ENVIRONMENT: 'development',
  DATABASE_URL: 'sqlite+aiosqlite:///./data/e2e.db',
  JWT_SECRET: 'e2e-throwaway-secret-not-for-production',
  SESSION_COOKIE_SECURE: 'false',
  // Keep auth rate limits from tripping across a full suite run.
  NETPLANNER_RATE_LIMIT_ENABLED: '0',
};

export default defineConfig({
  testDir: './e2e',
  // Fully parallel within a file is fine, but a fresh DB per run is shared
  // state — keep workers serialized so registration/login ordering is stable.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI
    ? [['list'], ['html', { open: 'never' }]]
    : [['list']],
  timeout: 30_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    // Registers one user and saves its session cookie so the authenticated
    // specs don't each re-login (faster, and avoids the auth rate limit).
    { name: 'setup', testMatch: /.*\.setup\.js/ },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],

  webServer: [
    {
      command: `sh -c "rm -f data/e2e.db && uv run uvicorn app.main:app --host ${HOST} --port ${BACKEND_PORT}"`,
      cwd: '../backend',
      url: `http://${HOST}:${BACKEND_PORT}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: backendEnv,
    },
    {
      command: `npm run dev -- --host ${HOST} --port ${FRONTEND_PORT} --strictPort`,
      url: BASE_URL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      // Point the dev-server /api proxy at the E2E backend's non-default port.
      env: { VITE_API_PROXY: `http://${HOST}:${BACKEND_PORT}` },
    },
  ],
});
