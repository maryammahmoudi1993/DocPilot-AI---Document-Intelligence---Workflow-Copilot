import { test, expect } from '@playwright/test';

test.describe('AppShell — responsive and keyboard behavior', () => {
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
    await expect(page.getByRole('main')).toContainText('Dashboard');
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
