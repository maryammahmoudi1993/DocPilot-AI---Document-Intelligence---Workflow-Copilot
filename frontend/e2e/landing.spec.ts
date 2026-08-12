import { test, expect } from '@playwright/test';

/** Landing → demo CTA is pure client-side routing (no backend call), so
 * this is fully coverable without a live API — see sign-in.spec.ts for
 * the same reasoning on why deeper auth flows live in the Vitest+MSW
 * suite instead (src/test/Home.test.tsx covers the honest-labeling and
 * no-unsupported-claim checks at that layer). */
test.describe('Landing page — CTA routing and responsive layout', () => {
  test('the primary CTA navigates to sign-in', async ({ page }) => {
    await page.goto('/');

    await page.getByRole('link', { name: 'Explore the demo workspace' }).first().click();

    await expect(page).toHaveURL(/\/sign-in$/);
  });

  test('renders without horizontal overflow at a common mobile width', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');

    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 1);
    await expect(page.locator('h1')).toBeVisible();
  });
});
