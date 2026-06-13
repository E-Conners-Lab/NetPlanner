import { test, expect } from '@playwright/test';
import { createProjectViaUI, openProject, sidebarLink } from './helpers.js';

/**
 * Guards react-router-dom routing (critical for the v6 → v7 upgrade): from a
 * project, every tool route must resolve and render its page heading.
 */
test('navigate from a project to each tool page', async ({ page }) => {
  const name = `Nav Project ${Date.now()}`;
  await createProjectViaUI(page, name);
  await openProject(page, name);

  const tools = [
    { link: 'AI Advisor', heading: 'AI Advisor' },
    { link: 'TCO Calculator', heading: 'TCO Calculator' },
    { link: 'Comparison', heading: 'Vendor Comparison' },
    { link: 'Reports', heading: 'Reports' },
  ];

  for (const tool of tools) {
    // Sidebar link (project section) navigates to the tool route.
    await sidebarLink(page, tool.link).click();
    await expect(page.getByRole('heading', { name: tool.heading })).toBeVisible();
    // Back to the project overview between hops via the sidebar.
    await sidebarLink(page, 'Overview').click();
    await expect(page.getByRole('heading', { name })).toBeVisible();
  }
});

test('unknown route redirects to the dashboard', async ({ page }) => {
  await page.goto('/this/does/not/exist');
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
});
