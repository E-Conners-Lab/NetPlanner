import { test, expect } from '@playwright/test';
import { createProjectViaUI, openProject, sidebarLink } from './helpers.js';

/**
 * TCO is a deterministic backend calculation (no LLM) rendered with recharts.
 * Exercises the full input → calculate → results → save flow, and asserts the
 * recharts SVG renders (guards the React 19 render path through recharts).
 */
test('calculate a TCO scenario and save it', async ({ page }) => {
  const name = `TCO Project ${Date.now()}`;
  await createProjectViaUI(page, name);
  await openProject(page, name);

  await sidebarLink(page, 'TCO Calculator').click();
  await expect(page.getByRole('heading', { name: 'TCO Calculator' })).toBeVisible();

  // Required inputs.
  await page.locator('#tco-scenario-name').fill('Baseline Refresh');
  await page.locator('#tco-device-count').fill('48');
  await page.locator('#tco-hardware-cost').fill('1200');
  await page.locator('#tco-licensing-cost').fill('180');

  await page.getByRole('button', { name: 'Calculate TCO' }).click();

  // Results panel + recharts chart render. `exact` pins the total-badge
  // label span; without it the substring also matches the wrapping div
  // (label + amount) → strict-mode "2 elements" flake.
  await expect(
    page.getByText('Total Cost of Ownership', { exact: true })
  ).toBeVisible();
  await expect(page.locator('.recharts-surface, svg').first()).toBeVisible();

  // Persist the scenario.
  await page.getByRole('button', { name: /^Save scenario/ }).click();
  await expect(page.getByText('Scenario saved successfully.')).toBeVisible();
});
