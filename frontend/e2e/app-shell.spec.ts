import { test, expect, type Page } from '@playwright/test';

/** No live backend in this sandbox (see e2e/sign-in.spec.ts) — /app/*
 * routes are protected (Phase 2B), so these shell/viewport tests need a
 * mocked signed-in session or they'd just redirect to /sign-in. */
async function mockSignedInSession(page: Page) {
  await page.route('**/api/auth/session/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user: { id: 'user-1', email: 'owner@demo.docpilot.ai', first_name: 'Demo', last_name: 'Owner' },
        workspaces: [{ id: 'ws-1', name: 'Demo Workspace', slug: 'demo-workspace', role: 'owner' }],
        active_workspace_id: 'ws-1',
      }),
    }),
  );
  await page.route('**/api/auth/refresh/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ access: 'fake-access-token' }),
    }),
  );
  await page.route('**/api/auth/active-workspace/', (route) => route.fulfill({ status: 204 }));
}

test.describe('AppShell — responsive and keyboard behavior', () => {
  test.beforeEach(async ({ page }) => {
    await mockSignedInSession(page);
  });

  test('desktop sidebar is visible and collapsible at 1440px', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/app/dashboard');

    const sidebar = page.getByRole('navigation', { name: 'Primary' });
    await expect(sidebar).toBeVisible();
    await expect(sidebar.getByRole('link', { name: 'Documents' })).toBeVisible();

    await page.getByRole('button', { name: /collapse sidebar/i }).click();
    // Labels disappear when collapsed; the icon-only link keeps its name.
    await expect(sidebar.getByText('Documents', { exact: true })).toBeHidden();
    await expect(sidebar.getByRole('link', { name: 'Documents' })).toBeVisible();
  });

  test('desktop sidebar remains usable at 1280px', async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.goto('/app/dashboard');

    await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
    // The Dashboard page's own heading is a personalized greeting, not
    // the literal word "Dashboard" (that's the sidebar nav item's
    // label, already asserted above) — "Recent documents" is static
    // content on the page regardless of whether its data queries
    // (unmocked here) succeed or fail.
    await expect(page.getByRole('main')).toContainText('Recent documents');
  });

  test('mobile navigation drawer opens and traps focus at 768px', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/app/dashboard');

    // Below the lg breakpoint the inline sidebar is not rendered at all.
    await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(0);

    await page.getByRole('button', { name: /open navigation menu/i }).click();
    const dialog = page.getByRole('dialog', { name: 'DocPilot AI' });
    await expect(dialog).toBeVisible();
    await expect(dialog.getByRole('link', { name: 'Documents' })).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
  });

  test('sidebar nav is reachable by keyboard alone', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto('/app/dashboard');

    await page.getByRole('link', { name: 'Documents' }).focus();
    await expect(page.getByRole('link', { name: 'Documents' })).toBeFocused();
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/app\/documents$/);
  });
});
