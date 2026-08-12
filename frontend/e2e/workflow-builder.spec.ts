import { test, expect, type Page } from '@playwright/test';

/**
 * No live backend in this sandbox (see e2e/documents.spec.ts) — the
 * full graph-validation/execution behavior is covered by the
 * Vitest + Testing Library + MSW suite (src/test/WorkflowBuilder.test.tsx).
 * This spec covers the create/test/activate scenario end to end against
 * a real browser and router, using the palette's click-to-add path
 * (rather than pointer drag-and-drop, which is inherently flaky to
 * simulate in Playwright) — the same interaction the keyboard-only path
 * uses, so it's a faithful exercise of the real UI.
 */
async function mockWorkflowScenario(page: Page) {
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
  await page.route('**/api/workspaces/ws-1/workflows/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 'wf-1', name: 'Invoice approval', is_active: false, created_at: '', updated_at: '' },
      ]),
    }),
  );
  await page.route('**/api/workspaces/ws-1/workflows/wf-1/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'wf-1',
        name: 'Invoice approval',
        is_active: false,
        active_version: null,
        draft_version: {
          id: 'ver-1',
          version_number: 1,
          status: 'draft',
          nodes: [],
          edges: [],
          created_at: '',
          activated_at: null,
        },
        created_at: '',
        updated_at: '',
      }),
    }),
  );
  await page.route('**/api/workspaces/ws-1/workflows/wf-1/draft/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'ver-1',
        version_number: 1,
        status: 'draft',
        nodes: [{ node_key: 'node-1', node_type: 'trigger', kind: 'document_uploaded', config: {}, position: { x: 0, y: 0 } }],
        edges: [],
        created_at: '',
        activated_at: null,
        validation_errors: [],
      }),
    }),
  );
  await page.route('**/api/workspaces/ws-1/workflows/wf-1/test-run/', (route) =>
    route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'run-1',
        status: 'completed',
        trigger_context: {},
        is_test_run: true,
        error_code: '',
        step_runs: [],
        started_at: null,
        completed_at: null,
        created_at: '',
      }),
    }),
  );
  await page.route('**/api/workspaces/ws-1/workflows/wf-1/runs/', (route) =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) }),
  );
  await page.route('**/api/workspaces/ws-1/workflows/wf-1/activate/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'ver-1',
        version_number: 1,
        status: 'active',
        nodes: [],
        edges: [],
        created_at: '',
        activated_at: '2026-08-12T00:00:00Z',
      }),
    }),
  );
}

test.describe('Workflow Builder — create/test/activate scenario', () => {
  test.beforeEach(async ({ page }) => {
    await mockWorkflowScenario(page);
  });

  test('adds a node, saves, and test-runs a workflow', async ({ page }) => {
    await page.goto('/app/workflows');

    await page.getByText('Invoice approval').click();
    await page.getByRole('button', { name: 'Document uploaded' }).first().click();
    await page.getByRole('button', { name: /save/i }).click();
    await page.getByRole('button', { name: /test run/i }).click();

    await expect(page.getByRole('button', { name: /execution log/i })).toBeVisible();
  });
});
