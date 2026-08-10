import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { demoWorkspaces } from './handlers';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

function errorBody(code: string, message: string, details: unknown = null) {
  return { error: { code, message, details } };
}

/** Fixtures matching the real backend contract (apps.documents
 * serializers — see backend/apps/documents/serializers.py). Kept in one
 * place so Documents.test.tsx and any future dev-mode mocking share a
 * single source of truth instead of drifting. */
export const demoDocuments = [
  {
    id: 'doc-1',
    filename: 'acme-invoice-0142.pdf',
    content_type: 'application/pdf',
    size_bytes: 245_760,
    checksum_sha256: 'a'.repeat(64),
    status: 'uploaded' as const,
    uploaded_by: { id: 'user-1', email: 'owner@demo.docpilot.ai', first_name: 'Demo', last_name: 'Owner' },
    created_at: '2026-08-08T10:15:00Z',
    archived_at: null,
  },
  {
    id: 'doc-2',
    filename: 'vendor-contract-2026.docx',
    content_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    size_bytes: 88_212,
    checksum_sha256: 'b'.repeat(64),
    status: 'archived' as const,
    uploaded_by: { id: 'user-1', email: 'owner@demo.docpilot.ai', first_name: 'Demo', last_name: 'Owner' },
    created_at: '2026-08-01T09:00:00Z',
    archived_at: '2026-08-05T12:00:00Z',
  },
];

/** Workspace-scoped document handlers for an already-signed-in session —
 * spread alongside `signedInHandlers` via server.use(...) in tests that
 * exercise the Documents page. Uses `demoWorkspaces[0]` as the active
 * workspace, matching `signedInHandlers`' `active_workspace_id`. */
export const documentHandlers = [
  http.get(`${API}/workspaces/${WORKSPACE_ID}/documents/`, ({ request }) => {
    const url = new URL(request.url);
    const search = url.searchParams.get('search')?.toLowerCase();
    const status = url.searchParams.get('status');

    let results = demoDocuments;
    if (search) results = results.filter((doc) => doc.filename.toLowerCase().includes(search));
    if (status) results = results.filter((doc) => doc.status === status);

    return HttpResponse.json({ count: results.length, next: null, previous: null, results });
  }),

  http.get(`${API}/workspaces/${WORKSPACE_ID}/documents/:documentId/`, ({ params }) => {
    const document = demoDocuments.find((doc) => doc.id === params.documentId);
    if (!document) {
      return HttpResponse.json(errorBody('not_found', 'Not found.'), { status: 404 });
    }
    return HttpResponse.json({
      ...document,
      download_url: `https://storage.example.com/${document.id}?signature=demo`,
    });
  }),

  http.post(`${API}/workspaces/${WORKSPACE_ID}/documents/:documentId/archive/`, ({ params }) => {
    const document = demoDocuments.find((doc) => doc.id === params.documentId);
    if (!document) {
      return HttpResponse.json(errorBody('not_found', 'Not found.'), { status: 404 });
    }
    if (document.status === 'archived') {
      return HttpResponse.json(
        errorBody('validation_error', 'Validation failed.', { status: 'Document is already archived.' }),
        { status: 400 },
      );
    }
    return HttpResponse.json({ ...document, status: 'archived', archived_at: '2026-08-10T00:00:00Z' });
  }),

  http.delete(`${API}/workspaces/${WORKSPACE_ID}/documents/:documentId/`, ({ params }) => {
    const document = demoDocuments.find((doc) => doc.id === params.documentId);
    if (!document) {
      return HttpResponse.json(errorBody('not_found', 'Not found.'), { status: 404 });
    }
    return new HttpResponse(null, { status: 204 });
  }),

  http.post(`${API}/workspaces/${WORKSPACE_ID}/documents/bulk-archive/`, async ({ request }) => {
    const body = (await request.json()) as { document_ids: string[] };
    const unknown = body.document_ids.filter((id) => !demoDocuments.some((doc) => doc.id === id));
    if (unknown.length > 0) {
      return HttpResponse.json(
        errorBody('validation_error', 'Validation failed.', { document_ids: `Unknown document ids: [${unknown.join(', ')}]` }),
        { status: 400 },
      );
    }
    const updated = demoDocuments
      .filter((doc) => body.document_ids.includes(doc.id))
      .map((doc) => ({ ...doc, status: 'archived' as const, archived_at: '2026-08-10T00:00:00Z' }));
    return HttpResponse.json(updated);
  }),

  http.post(`${API}/workspaces/${WORKSPACE_ID}/documents/bulk-delete/`, async ({ request }) => {
    const body = (await request.json()) as { document_ids: string[] };
    const unknown = body.document_ids.filter((id) => !demoDocuments.some((doc) => doc.id === id));
    if (unknown.length > 0) {
      return HttpResponse.json(
        errorBody('validation_error', 'Validation failed.', { document_ids: `Unknown document ids: [${unknown.join(', ')}]` }),
        { status: 400 },
      );
    }
    return new HttpResponse(null, { status: 204 });
  }),
];

export function uploadSuccessHandler() {
  return http.post(`${API}/workspaces/${WORKSPACE_ID}/documents/`, () =>
    HttpResponse.json(
      {
        id: 'doc-new',
        filename: 'new-upload.pdf',
        content_type: 'application/pdf',
        size_bytes: 1024,
        checksum_sha256: 'c'.repeat(64),
        status: 'uploaded',
        uploaded_by: { id: 'user-1', email: 'owner@demo.docpilot.ai', first_name: 'Demo', last_name: 'Owner' },
        created_at: '2026-08-10T00:00:00Z',
        archived_at: null,
      },
      { status: 201 },
    ),
  );
}

export function uploadErrorHandler(code: string, message: string, details: unknown = null) {
  return http.post(`${API}/workspaces/${WORKSPACE_ID}/documents/`, () =>
    HttpResponse.json(errorBody(code, message, details), { status: 400 }),
  );
}
