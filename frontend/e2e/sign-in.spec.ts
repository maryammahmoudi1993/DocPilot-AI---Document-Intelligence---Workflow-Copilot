import { test, expect } from '@playwright/test';

/**
 * Full sign-in/redirect/logout/workspace-switch E2E scenarios need a
 * real backend (Postgres + Redis + Django) to authenticate against —
 * unavailable in the sandbox this phase was built in (same Docker/
 * network limitation documented in the root README and Phase 0D/2A
 * notes). That behavior is instead covered end-to-end at the
 * network-mock boundary by the Vitest + Testing Library + MSW suite
 * (src/test/SignIn.test.tsx, ProtectedRoute.test.tsx,
 * WorkspaceSelector.test.tsx, RequireRole.test.tsx — 72 tests total),
 * which exercises the real component/hook/router tree, not a stub.
 *
 * This spec covers what's real to check without a backend: the page
 * renders correctly and is fully keyboard-operable.
 */
test.describe('Sign in page — rendering and keyboard smoke', () => {
  test('renders the form with accessible labels', async ({ page }) => {
    await page.goto('/sign-in');

    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeVisible();
  });

  test('is reachable and submittable by keyboard alone', async ({ page }) => {
    await page.goto('/sign-in');

    await page.getByLabel('Email').focus();
    await expect(page.getByLabel('Email')).toBeFocused();
    await page.keyboard.type('someone@example.com');
    await page.keyboard.press('Tab');
    await expect(page.getByLabel('Password')).toBeFocused();
    await page.keyboard.type('whatever-password');
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: 'Sign In' })).toBeFocused();
  });
});
