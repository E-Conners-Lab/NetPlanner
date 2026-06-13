import { test, expect } from '@playwright/test';
import { createProjectViaUI, openProject, sidebarLink } from './helpers.js';

/**
 * Vendor comparison runs live research + AI synthesis on the backend, so the
 * POST is STUBBED (AI-3/AI-4: never hit a paid model in tests). This still
 * exercises the form → submit → matrix-render flow that the upgrades could
 * break.
 */
test('generate a vendor comparison and render the matrix', async ({ page }) => {
  const name = `Comparison Project ${Date.now()}`;
  await createProjectViaUI(page, name);
  await openProject(page, name);

  await sidebarLink(page, 'Comparison').click();
  await expect(page.getByRole('heading', { name: 'Vendor Comparison' })).toBeVisible();

  // Stub the synthesis call with a deterministic matrix matching the schema.
  await page.route('**/api/projects/*/comparison', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const body = {
      id: 'cmp-e2e-1',
      project_id: 'e2e',
      vendors: ['Cisco', 'Juniper'],
      criteria: ['Pricing', 'Support & SLA', 'Scalability'],
      matrix: {
        Cisco: {
          Pricing: { value: 'Premium', source: 'vendor', confidence: 'high' },
          'Support & SLA': { value: '24/7 TAC', source: 'vendor', confidence: 'high' },
          Scalability: { value: 'Excellent', source: 'vendor', confidence: 'medium' },
        },
        Juniper: {
          Pricing: { value: 'Competitive', source: 'vendor', confidence: 'high' },
          'Support & SLA': { value: 'JTAC', source: 'vendor', confidence: 'medium' },
          Scalability: { value: 'Strong', source: 'vendor', confidence: 'medium' },
        },
      },
      summary: 'Both are strong; Juniper edges on price, Cisco on support depth.',
      created_at: new Date().toISOString(),
    };
    await route.fulfill({ json: body });
  });

  // Fill the two default vendor rows; criteria come prefilled.
  const vendorInputs = page.getByPlaceholder(/^Vendor \d/);
  await vendorInputs.nth(0).fill('Cisco');
  await vendorInputs.nth(1).fill('Juniper');

  await page.getByRole('button', { name: 'Generate comparison' }).click();

  await expect(page.getByRole('heading', { name: 'Comparison Matrix' })).toBeVisible();
  await expect(page.getByText('Premium')).toBeVisible();
  await expect(page.getByText('Competitive')).toBeVisible();
  await expect(
    page.getByText('Juniper edges on price', { exact: false })
  ).toBeVisible();
});
