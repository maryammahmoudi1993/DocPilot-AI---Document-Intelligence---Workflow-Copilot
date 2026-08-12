import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('homepage loads successfully', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('navigation')).toContainText('DocPilot AI');
    await expect(page.locator('h1')).toBeVisible();
  });

  test('404 page displays for unknown routes', async ({ page }) => {
    await page.goto('/unknown-route');
    await expect(page.locator('h1')).toContainText('404');
  });
});
