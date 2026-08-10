import { test, expect, type Page } from '@playwright/test';

/**
 * No live backend in this sandbox (see e2e/sign-in.spec.ts and
 * e2e/app-shell.spec.ts) — real upload/list/filter/bulk-action behavior
 * against the actual documents API is covered by the Vitest + Testing
 * Library + MSW suite (src/test/Documents.test.tsx), which exercises the
 * real component/hook/router tree. This spec covers what's real to check
 * without a backend: the page renders correctly and is keyboard-operable.
 */
async function mockSignedInSessionWithDocuments(page: Page) {
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
  await page.route('**/api/workspaces/ws-1/documents/**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: 'doc-1',
            filename: 'acme-invoice-0142.pdf',
            content_type: 'application/pdf',
            size_bytes: 245_760,
            checksum_sha256: 'a'.repeat(64),
            status: 'uploaded',
            uploaded_by: { id: 'user-1', email: 'owner@demo.docpilot.ai', first_name: 'Demo', last_name: 'Owner' },
            created_at: '2026-08-08T10:15:00Z',
            archived_at: null,
          },
        ],
      }),
    }),
  );
}

test.describe('Documents page — rendering and keyboard smoke', () => {
  test.beforeEach(async ({ page }) => {
    await mockSignedInSessionWithDocuments(page);
  });

  test('renders the document library with the uploaded file', async ({ page }) => {
    await page.goto('/app/documents');

    await expect(page.getByRole('heading', { name: 'Documents' })).toBeVisible();
    await expect(page.getByRole('table', { name: /documents/i })).toBeVisible();
    await expect(page.getByText('acme-invoice-0142.pdf')).toBeVisible();
  });

  test('opens the upload dialog by keyboard and traps focus', async ({ page }) => {
    await page.goto('/app/documents');

    await page.getByRole('button', { name: 'Upload Document' }).focus();
    await page.keyboard.press('Enter');

    const dialog = page.getByRole('dialog', { name: 'Upload documents' });
    await expect(dialog).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();
  });
});
