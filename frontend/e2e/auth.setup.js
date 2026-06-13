import { test as setup, expect } from '@playwright/test';
import { uniqueEmail, E2E_PASSWORD } from './helpers.js';

const AUTH_FILE = 'e2e/.auth/user.json';

/**
 * One-time auth: register a user and persist its session cookie so the
 * authenticated specs reuse it via storageState. Runs before the chromium
 * project (declared as its dependency in playwright.config.js).
 */
setup('authenticate', async ({ page }) => {
  const email = uniqueEmail('owner');

  await page.goto('/register');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(E2E_PASSWORD);
  await page.getByRole('button', { name: 'Create account' }).click();

  // Registration sets the httpOnly session cookie and lands on the dashboard.
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();

  await page.context().storageState({ path: AUTH_FILE });
});
