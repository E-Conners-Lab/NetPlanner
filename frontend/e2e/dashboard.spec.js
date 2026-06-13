import { test, expect } from '@playwright/test';
import { createProjectViaUI, openProject } from './helpers.js';

// Authenticated via the shared storageState (see playwright.config.js).

test('create a project, open it, then delete it', async ({ page }) => {
  const name = `Campus LAN ${Date.now()}`;

  // Create
  await createProjectViaUI(page, name);

  // Open → detail page
  await openProject(page, name);
  await expect(page.getByRole('heading', { name })).toBeVisible();

  // Delete via confirm dialog
  await page.getByRole('button', { name: 'Delete' }).click();
  await expect(page.getByRole('heading', { name: 'Delete Project' })).toBeVisible();
  await page.getByRole('button', { name: 'Delete Project' }).click();

  // Back on the dashboard, the card is gone.
  await expect(page).toHaveURL(/\/$|\/$/);
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  await expect(page.getByText(name, { exact: true })).toHaveCount(0);
});

test('edit a project name and see it reflected', async ({ page }) => {
  const name = `Edit Me ${Date.now()}`;
  const renamed = `${name} (renamed)`;

  await createProjectViaUI(page, name);
  await openProject(page, name);

  await page.getByRole('button', { name: 'Edit' }).click();
  await expect(page.getByRole('heading', { name: 'Edit Project' })).toBeVisible();
  await page.locator('#project-name').fill(renamed);
  await page.getByRole('button', { name: 'Save Changes' }).click();

  await expect(page.getByRole('heading', { name: renamed })).toBeVisible();
});
