import { test, expect, type Page } from '@playwright/test';

/**
 * No live backend in this sandbox (see e2e/documents.spec.ts) — the
 * full retrieval/grounding/citation behavior is covered by the
 * Vitest + Testing Library + MSW suite (src/test/AiAssistant.test.tsx).
 * This spec covers the ask-question/open-citation scenario end to end
 * against a real browser and router.
 */
async function mockAssistantScenario(page: Page) {
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
      body: JSON.stringify({ count: 0, next: null, previous: null, results: [] }),
    }),
  );
  await page.route('**/api/workspaces/ws-1/assistant/conversations/', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) });
    }
    return route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'conv-1',
        title: '',
        document_scope: [],
        messages: [],
        created_at: '2026-08-12T00:00:00Z',
        updated_at: '2026-08-12T00:00:00Z',
      }),
    });
  });
  const assistantMessage = {
    id: 'msg-1',
    role: 'assistant',
    content: 'Based on 1 matching passage the total due is $1,200.00.',
    is_insufficient_evidence: false,
    citations: [
      {
        id: 'c1',
        document_id: 'doc-1',
        filename: 'acme-invoice-0142.pdf',
        page_number: 1,
        snippet: 'Total due: $1,200.00',
        order: 0,
      },
    ],
    created_at: '2026-08-12T00:00:05Z',
  };
  await page.route('**/api/workspaces/ws-1/assistant/conversations/conv-1/messages/', (route) =>
    route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(assistantMessage) }),
  );
  // Fetched again after asking (the mutation invalidates the
  // conversation-detail query) — without this, the new message/citation
  // would never actually render even though the ask itself succeeded.
  await page.route('**/api/workspaces/ws-1/assistant/conversations/conv-1/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'conv-1',
        title: '',
        document_scope: [],
        messages: [
          {
            id: 'msg-user-1',
            role: 'user',
            content: 'What is the total on the most recent invoice?',
            is_insufficient_evidence: false,
            citations: [],
            created_at: '2026-08-12T00:00:04Z',
          },
          assistantMessage,
        ],
        created_at: '2026-08-12T00:00:00Z',
        updated_at: '2026-08-12T00:00:05Z',
      }),
    }),
  );
  await page.route('**/api/workspaces/ws-1/documents/doc-1/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'doc-1',
        filename: 'acme-invoice-0142.pdf',
        content_type: 'application/pdf',
        size_bytes: 245_760,
        checksum_sha256: 'a'.repeat(64),
        status: 'uploaded',
        uploaded_by: { id: 'user-1', email: 'owner@demo.docpilot.ai', first_name: 'Demo', last_name: 'Owner' },
        created_at: '2026-08-08T10:15:00Z',
        archived_at: null,
        download_url: 'data:application/pdf;base64,JVBERi0xLjQK',
      }),
    }),
  );
}

test.describe('AI Assistant — ask-question and open-citation scenario', () => {
  test.beforeEach(async ({ page }) => {
    await mockAssistantScenario(page);
  });

  test('asks a question and opens the returned citation', async ({ page }) => {
    await page.goto('/app/assistant');

    await page.getByRole('button', { name: /what is the total on the most recent invoice/i }).click();

    const citation = page.getByRole('button', { name: /acme-invoice-0142\.pdf · p\.1/i });
    await expect(citation).toBeVisible();

    await citation.click();
    await expect(page.getByRole('heading', { name: 'Source' })).toBeVisible();
  });
});
