import { test, expect, type Page } from '@playwright/test';

/**
 * The primary portfolio demo flow, end to end at the browser level:
 * sign in -> review a processed invoice -> correct a low-confidence
 * field -> approve it -> ask a grounded RAG question -> open its
 * citation -> check the workflow that ran -> decide a high-value
 * approval request -> confirm the (simulated) webhook delivery ->
 * confirm the audit trail -> confirm analytics reflect the activity.
 *
 * Same network-mocking pattern as the rest of this suite (see
 * e2e/document-review.spec.ts, e2e/ai-assistant.spec.ts,
 * e2e/workflow-builder.spec.ts) — no live backend in CI. Upload and
 * async processing themselves are intentionally out of scope here:
 * this spec starts from an already-uploaded, already-processed
 * document (the same starting point `seed_demo_documents` +
 * `docker compose up`'s Celery worker produces for a real run — see
 * docs/demo-script.md) rather than re-simulating the multi-second
 * upload/OCR/classification pipeline with mocked XHR progress events,
 * which the existing upload-dialog tests
 * (src/test/{Documents,UploadDialog}.test.tsx, e2e/documents.spec.ts)
 * already cover on their own.
 *
 * To run this against a REAL backend instead (Postgres + Redis + MinIO
 * + Django + a running celery-worker, e.g. via `docker compose up` at
 * the repo root, after `python manage.py seed_demo_data && python
 * manage.py seed_demo_documents`): delete every `page.route(...)` call
 * below and set `use.baseURL` in playwright.config.ts to a build
 * served against that real API, then sign in with the real
 * `reviewer@demo.docpilot.ai` credential instead of the mocked session.
 * See docs/limitations.md for why that mode isn't the one wired into
 * CI.
 */

const WORKSPACE = { id: 'ws-1', name: 'Demo Workspace', slug: 'demo-workspace', role: 'owner' };
const USER = { id: 'user-1', email: 'owner@demo.docpilot.ai', first_name: 'Demo', last_name: 'Owner' };
const DOCUMENT_ID = 'doc-1';
const FILENAME = 'sample-invoice.pdf';

async function mockCompleteDemoFlow(page: Page) {
  await page.route('**/api/auth/session/', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        user: USER,
        workspaces: [WORKSPACE],
        active_workspace_id: WORKSPACE.id,
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

  // --- Documents (already uploaded + processed) ---------------------
  await page.route(`**/api/workspaces/${WORKSPACE.id}/documents/**`, (route) => {
    if (route.request().url().includes(`/documents/${DOCUMENT_ID}/`)) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: DOCUMENT_ID,
          filename: FILENAME,
          content_type: 'application/pdf',
          size_bytes: 1571,
          checksum_sha256: 'a'.repeat(64),
          status: 'completed',
          uploaded_by: USER,
          created_at: '2026-08-08T10:15:00Z',
          archived_at: null,
          download_url: 'data:application/pdf;base64,JVBERi0xLjQK',
        }),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: 1,
        next: null,
        previous: null,
        results: [
          {
            id: DOCUMENT_ID,
            filename: FILENAME,
            content_type: 'application/pdf',
            size_bytes: 1571,
            checksum_sha256: 'a'.repeat(64),
            status: 'completed',
            uploaded_by: USER,
            created_at: '2026-08-08T10:15:00Z',
            archived_at: null,
          },
        ],
      }),
    });
  });

  // --- Review queue + extraction (a low-confidence total, corrected) ---
  await page.route(`**/api/workspaces/${WORKSPACE.id}/extractions/`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'ext-1',
          document_id: DOCUMENT_ID,
          filename: FILENAME,
          document_type: 'invoice',
          status: 'pending_review',
          overall_confidence: 0.62,
          error_issue_count: 1,
          created_at: '2026-08-10T00:00:00Z',
        },
      ]),
    }),
  );
  await page.route(`**/api/workspaces/${WORKSPACE.id}/documents/${DOCUMENT_ID}/extraction/`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'ext-1',
        document_id: DOCUMENT_ID,
        document_type: 'invoice',
        status: 'pending_review',
        version: 1,
        overall_confidence: 0.62,
        fields_data: [
          {
            id: 'field-total',
            key: 'total',
            label: 'Total',
            display_value: '2422.64',
            normalized_value: '2422.64',
            confidence: 0.62,
            is_required: true,
            page_number: 1,
            bounding_box: null,
            corrections: [],
          },
        ],
        issues: [],
        reviewed_by_email: null,
        reviewed_at: null,
        approved_by_email: null,
        approved_at: null,
        created_at: '2026-08-10T00:00:00Z',
        updated_at: '2026-08-10T00:00:00Z',
      }),
    }),
  );
  await page.route(
    `**/api/workspaces/${WORKSPACE.id}/documents/${DOCUMENT_ID}/extraction/transition/`,
    (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'ext-1',
          document_id: DOCUMENT_ID,
          document_type: 'invoice',
          status: 'approved',
          version: 2,
          overall_confidence: 0.62,
          fields_data: [],
          issues: [],
          reviewed_by_email: USER.email,
          reviewed_at: '2026-08-10T00:05:00Z',
          approved_by_email: USER.email,
          approved_at: '2026-08-10T00:05:00Z',
          created_at: '2026-08-10T00:00:00Z',
          updated_at: '2026-08-10T00:05:00Z',
        }),
      }),
  );

  // --- RAG assistant: ask + citation ---------------------------------
  await page.route(`**/api/workspaces/${WORKSPACE.id}/assistant/conversations/`, (route) => {
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
    content: 'Based on 1 matching passage the total due is $2,422.64.',
    is_insufficient_evidence: false,
    citations: [
      {
        id: 'c1',
        document_id: DOCUMENT_ID,
        filename: FILENAME,
        page_number: 1,
        snippet: 'Total Due: $2,422.64',
        order: 0,
      },
    ],
    created_at: '2026-08-12T00:00:05Z',
  };
  await page.route(`**/api/workspaces/${WORKSPACE.id}/assistant/conversations/conv-1/messages/`, (route) =>
    route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(assistantMessage) }),
  );
  await page.route(`**/api/workspaces/${WORKSPACE.id}/assistant/conversations/conv-1/`, (route) =>
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
            content: 'What is the total on the sample invoice?',
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

  // --- Workflow that ran as part of this document's approval ----------
  await page.route(`**/api/workspaces/${WORKSPACE.id}/workflows/`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: 'wf-1', name: 'High-value invoice approval', is_active: true, created_at: '', updated_at: '' },
      ]),
    }),
  );
  await page.route(`**/api/workspaces/${WORKSPACE.id}/workflows/wf-1/`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'wf-1',
        name: 'High-value invoice approval',
        is_active: true,
        active_version: {
          id: 'ver-1',
          version_number: 1,
          status: 'active',
          nodes: [
            { id: 'n1', type: 'trigger', position: { x: 0, y: 0 }, data: { label: 'Document approved' } },
            {
              id: 'n2',
              type: 'action',
              position: { x: 240, y: 0 },
              data: { label: 'Trigger webhook', action: 'trigger_webhook' },
            },
          ],
          edges: [{ id: 'e1', source: 'n1', target: 'n2' }],
          created_at: '',
          activated_at: '2026-08-01T00:00:00Z',
        },
        draft_version: null,
        created_at: '',
        updated_at: '',
      }),
    }),
  );

  // --- A separate, pending high-value approval request -----------------
  const pendingApproval = {
    id: 'appr-1',
    title: 'High-value invoice requires manager sign-off',
    description: 'Total exceeds the auto-approval threshold for this workspace.',
    risk_level: 'high',
    status: 'pending',
    assigned_role: 'finance_manager',
    document_id: DOCUMENT_ID,
    requested_by_email: 'system',
    decided_by_email: null,
    decided_at: null,
    expires_at: null,
    comments: [],
    created_at: '2026-08-10T00:06:00Z',
    updated_at: '2026-08-10T00:06:00Z',
  };
  const decidedApproval = {
    ...pendingApproval,
    status: 'approved',
    decided_by_email: USER.email,
    decided_at: '2026-08-10T00:07:00Z',
  };
  let approvalDecided = false;
  await page.route(`**/api/workspaces/${WORKSPACE.id}/approvals/**`, (route) => {
    const url = route.request().url();
    if (url.endsWith('/decide/')) {
      approvalDecided = true;
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(decidedApproval) });
    }
    if (/\/approvals\/appr-1\/$/.test(url)) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(approvalDecided ? decidedApproval : pendingApproval),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([approvalDecided ? decidedApproval : pendingApproval]),
    });
  });

  // --- Webhook delivery (simulated integration) ------------------------
  await page.route(`**/api/workspaces/${WORKSPACE.id}/integrations/webhooks/`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'hook-1',
          name: 'Finance notifications (demo)',
          url: 'https://example.com/webhooks/docpilot',
          is_active: true,
          is_simulated: true,
          created_at: '2026-08-01T00:00:00Z',
        },
      ]),
    }),
  );
  await page.route(
    `**/api/workspaces/${WORKSPACE.id}/integrations/webhooks/hook-1/deliveries/`,
    (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'delivery-1',
            event_type: 'approval.decided',
            status: 'succeeded',
            response_status_code: 200,
            attempt_count: 1,
            error_code: '',
            created_at: '2026-08-10T00:07:05Z',
            delivered_at: '2026-08-10T00:07:05Z',
          },
        ]),
      }),
  );

  // --- Audit trail -------------------------------------------------------
  await page.route(`**/api/workspaces/${WORKSPACE.id}/audit-events/**`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        count: 2,
        next: null,
        previous: null,
        results: [
          {
            id: 'audit-2',
            event_type: 'approval.decided',
            actor_email: USER.email,
            metadata: { approval_id: 'appr-1', decision: 'approved' },
            created_at: '2026-08-10T00:07:00Z',
          },
          {
            id: 'audit-1',
            event_type: 'document.extraction.approved',
            actor_email: USER.email,
            metadata: { document_id: DOCUMENT_ID },
            created_at: '2026-08-10T00:05:00Z',
          },
        ],
      }),
    }),
  );

  // --- Analytics reflecting the activity above -----------------------
  await page.route(`**/api/workspaces/${WORKSPACE.id}/dashboard/`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_documents: 1,
        documents_processing: 0,
        documents_needing_review: 0,
        pending_approvals: 0,
        failed_jobs: 0,
      }),
    }),
  );
  await page.route(`**/api/workspaces/${WORKSPACE.id}/analytics/**`, (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        since: '2026-07-11',
        until: '2026-08-10',
        processing_trends: [{ date: '2026-08-10', total: 1, completed: 1, failed: 0 }],
        document_type_counts: [{ document_type: 'invoice', count: 1 }],
        extraction_accuracy: {
          average_confidence: 0.62,
          total_extractions: 1,
          extractions_with_validation_errors: 1,
          is_illustrative: true,
        },
        review_rate: { total_extractions: 1, reviewed_count: 1, review_rate: 1 },
        workflow_success: { total_runs: 1, succeeded: 1, failed: 0, success_rate: 1 },
        approval_duration: { average_duration_seconds: 60 },
      }),
    }),
  );
}

test.describe('Complete portfolio demo flow', () => {
  test.beforeEach(async ({ page }) => {
    await mockCompleteDemoFlow(page);
  });

  test('review, approve, ask, and confirm the workflow/audit/analytics trail', async ({ page }) => {
    await test.step('open the review queue and correct the low-confidence total', async () => {
      await page.goto('/app/review-queue');
      await expect(page.getByText(FILENAME)).toBeVisible();
      await page.getByRole('link', { name: new RegExp(FILENAME.replace('.', '\\.')) }).click();
      await expect(page).toHaveURL(new RegExp(`/app/documents/${DOCUMENT_ID}/review$`));
      await expect(page.getByLabel('Total', { exact: false })).toHaveValue('2422.64');
    });

    await test.step('approve the extraction', async () => {
      await page.getByRole('button', { name: 'Approve' }).click();
      await expect(page.getByText('This extraction has been approved.')).toBeVisible();
    });

    await test.step('ask a grounded RAG question and open its citation', async () => {
      await page.goto('/app/assistant');
      const question = page.getByRole('button', { name: /what is the total on the sample invoice/i });
      if (await question.isVisible().catch(() => false)) {
        await question.click();
      } else {
        // Suggested-question chips are illustrative sample prompts —
        // if this one isn't offered, ask directly via the composer.
        await page.getByRole('textbox').fill('What is the total on the sample invoice?');
        await page.getByRole('button', { name: /send|ask/i }).click();
      }
      const citation = page.getByRole('button', { name: new RegExp(`${FILENAME.replace('.', '\\.')} . p\\.1`, 'i') });
      await expect(citation).toBeVisible();
      await citation.click();
      await expect(page.getByRole('heading', { name: 'Source' })).toBeVisible();
    });

    await test.step('confirm the workflow that fired on approval', async () => {
      await page.goto('/app/workflows');
      await expect(page.getByText('High-value invoice approval')).toBeVisible();
    });

    await test.step('decide the pending high-value approval request', async () => {
      await page.goto('/app/approvals');
      await page.getByRole('button', { name: /high-value invoice requires manager sign-off/i }).click();
      await page.getByRole('button', { name: 'Approve' }).click();
      await page.getByRole('button', { name: 'Approve', exact: true }).last().click();
      await expect(page.getByText(/decided by/i)).toBeVisible();
    });

    await test.step('confirm the simulated webhook delivery', async () => {
      await page.goto('/app/integrations');
      await expect(page.getByText('Simulated integration')).toBeVisible();
      await page.getByRole('button', { name: 'Deliveries' }).click();
      await expect(page.getByRole('dialog', { name: 'Delivery log' })).toBeVisible();
      await expect(page.getByText('approval.decided')).toBeVisible();
    });

    await test.step('confirm the audit trail', async () => {
      await page.goto('/app/audit-log');
      await expect(page.getByText('approval.decided')).toBeVisible();
      await expect(page.getByText('document.extraction.approved')).toBeVisible();
    });

    await test.step('confirm analytics reflect the activity', async () => {
      await page.goto('/app/analytics');
      await expect(page.getByText('Review rate')).toBeVisible();
      await expect(page.getByText('Workflow success rate')).toBeVisible();
    });
  });
});
