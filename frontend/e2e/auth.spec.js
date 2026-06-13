import { test, expect } from '@playwright/test';
import { uniqueEmail, E2E_PASSWORD } from './helpers.js';

// These tests exercise the auth UI from a clean slate, so they must NOT inherit
// the shared logged-in session.
test.use({ storageState: { cookies: [], origins: [] } });

test('unauthenticated visit to a protected route redirects to /login', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('heading', { name: 'Sign in to NetPlanner' })).toBeVisible();
});

test('register → dashboard, logout → login, login → dashboard', async ({ page }) => {
  const email = uniqueEmail('authflow');

  // Register
  await page.goto('/register');
  await expect(
    page.getByRole('heading', { name: 'Create your NetPlanner account' })
  ).toBeVisible();
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(E2E_PASSWORD);
  await page.getByRole('button', { name: 'Create account' }).click();

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await expect(page.getByText(email)).toBeVisible(); // email shown in TopBar

  // Logout
  await page.getByRole('button', { name: 'Sign out' }).click();
  await expect(page).toHaveURL(/\/login$/);

  // Login again
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(E2E_PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
});

test('login with bad credentials shows an error and stays on /login', async ({ page }) => {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(uniqueEmail('nobody'));
  await page.locator('input[type="password"]').fill('wrongpassword99');
  await page.getByRole('button', { name: 'Sign in' }).click();

  await expect(page.getByText(/Login failed|Invalid|credentials/i)).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
});
