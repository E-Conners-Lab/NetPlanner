import { expect } from '@playwright/test';

/**
 * Shared E2E helpers. The suite drives the real UI end-to-end; these keep the
 * specs focused on the flow under test rather than on plumbing.
 */

// Meets the SEC-17 / Register page minimum of 12 characters.
export const E2E_PASSWORD = 'E2ePassw0rd!2026';

let counter = 0;

/** A unique email per call so re-runs never collide on the shared test DB. */
export function uniqueEmail(prefix = 'user') {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}@e2e.test`;
}

/** Register a fresh account through the UI. Lands on the dashboard on success. */
export async function registerViaUI(page, email, password = E2E_PASSWORD) {
  await page.goto('/register');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.getByRole('button', { name: 'Create account' }).click();
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
}

/** Create a project through the dashboard modal and wait for its card. */
export async function createProjectViaUI(page, name) {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await page.getByRole('button', { name: 'New Project' }).first().click();
  await page.locator('#project-name').fill(name);
  await page.getByRole('button', { name: 'Create Project' }).click();
  // The new project surfaces as a clickable card carrying its name.
  await expect(page.getByText(name, { exact: true })).toBeVisible();
}

/**
 * A sidebar nav link, scoped to the navigation landmark. Tool names (AI
 * Advisor, TCO Calculator, …) also appear as ProjectDetail tool cards, so an
 * unscoped getByRole('link') is ambiguous.
 */
export function sidebarLink(page, name) {
  return page.getByRole('navigation').getByRole('link', { name });
}

/** Open a project from the dashboard and land on its detail page. */
export async function openProject(page, name) {
  await page.goto('/');
  await page.getByText(name, { exact: true }).click();
  await expect(page.getByRole('heading', { name })).toBeVisible();
}
