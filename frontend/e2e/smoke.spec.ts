import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('homepage loads successfully', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('DocPilot AI');
  });

  test('404 page displays for unknown routes', async ({ page }) => {
    await page.goto('/unknown-route');
    await expect(page.locator('h1')).toContainText('404');
  });
});
