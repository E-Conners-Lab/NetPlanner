import { test, expect } from '@playwright/test';
import { createProjectViaUI, openProject, sidebarLink } from './helpers.js';

/**
 * Reports renders a PDF on the backend (weasyprint, native libs). We don't
 * generate a real PDF here — we verify the page loads and the Generate button
 * is correctly gated until a title + at least one artifact are chosen. That
 * covers the routing + form-state behavior the upgrades could break.
 */
test('reports page loads and gates the Generate button', async ({ page }) => {
  const name = `Reports Project ${Date.now()}`;
  await createProjectViaUI(page, name);
  await openProject(page, name);

  await sidebarLink(page, 'Reports').click();
  await expect(page.getByRole('heading', { name: 'Reports' })).toBeVisible();

  // With no title and no artifacts selected, generation is disabled.
  const generate = page.getByRole('button', { name: /Generate PDF/i });
  await expect(generate).toBeVisible();
  await expect(generate).toBeDisabled();

  // A title alone is not enough (no artifacts yet) — still disabled.
  await page.locator('#report-title').fill('Q3 Network Summary');
  await expect(generate).toBeDisabled();
});
