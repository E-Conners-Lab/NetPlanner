import { test, expect } from '@playwright/test';
import { createProjectViaUI, openProject, sidebarLink } from './helpers.js';

/**
 * The Advisor streams an LLM response over SSE. We STUB the endpoint (AI-3/AI-4:
 * never hit a paid model in tests) with a deterministic markdown payload, then
 * assert it RENDERS as markdown — this directly guards the react-markdown 9→10
 * upgrade (bold + list must still render to <strong>/<li>).
 */
test('advisor streams a response and renders it as markdown', async ({ page }) => {
  const name = `Advisor Project ${Date.now()}`;
  await createProjectViaUI(page, name);
  await openProject(page, name);

  await sidebarLink(page, 'AI Advisor').click();
  await expect(page.getByRole('heading', { name: 'AI Advisor' })).toBeVisible();

  // Stub the SSE stream with a token event (markdown) + a done event.
  await page.route('**/api/projects/*/advisor', async (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const md =
      'Use **Cisco** for this design because:\n\n- mature support\n- broad ecosystem';
    const body =
      `data: ${JSON.stringify({ type: 'token', content: md })}\n\n` +
      `data: ${JSON.stringify({ type: 'done', conversation_id: 'conv-e2e-1' })}\n\n`;
    await route.fulfill({
      status: 200,
      headers: { 'content-type': 'text/event-stream' },
      body,
    });
  });

  const input = page.getByPlaceholder(/Ask about TCO/i);
  await input.fill('Which vendor should I pick?');
  await page.getByRole('button', { name: 'Send' }).click();

  // User turn echoed.
  await expect(page.getByText('Which vendor should I pick?')).toBeVisible();
  // Assistant markdown rendered to real elements, not raw asterisks.
  await expect(page.locator('strong', { hasText: 'Cisco' })).toBeVisible();
  // A real <li> (not raw "- mature support") confirms the markdown list rendered.
  await expect(
    page.getByRole('listitem').filter({ hasText: 'mature support' })
  ).toBeVisible();
});
