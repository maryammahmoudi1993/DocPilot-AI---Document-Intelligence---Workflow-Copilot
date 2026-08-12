import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import type { DocumentExtraction, ExtractedField, ExtractionQueueItem } from '@/features/extraction/types';
import { demoWorkspaces } from './handlers';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

function errorBody(code: string, message: string, details: unknown = null) {
  return { error: { code, message, details } };
}

function buildField(overrides: Partial<ExtractedField> = {}): ExtractedField {
  return {
    id: 'field-total',
    key: 'total',
    label: 'Total',
    display_value: '110.00',
    normalized_value: '110.00',
    confidence: 0.92,
    is_required: true,
    page_number: 1,
    bounding_box: null,
    corrections: [],
    ...overrides,
  };
}

export function buildExtraction(overrides: Partial<DocumentExtraction> = {}): DocumentExtraction {
  return {
    id: 'extraction-1',
    document_id: 'doc-1',
    document_type: 'invoice',
    status: 'pending_review',
    version: 1,
    overall_confidence: 0.9,
    fields_data: [
      buildField({ id: 'field-vendor', key: 'vendor_name', label: 'Vendor name', display_value: 'Acme Supplies' }),
      buildField({ id: 'field-invoice-number', key: 'invoice_number', label: 'Invoice number', display_value: 'INV-1001' }),
      buildField({ id: 'field-total', key: 'total', label: 'Total', display_value: '110.00' }),
    ],
    issues: [],
    reviewed_by_email: null,
    reviewed_at: null,
    approved_by_email: null,
    approved_at: null,
    created_at: '2026-08-10T00:00:00Z',
    updated_at: '2026-08-10T00:00:00Z',
    ...overrides,
  };
}

export function extractionQueueHandler(items: ExtractionQueueItem[]) {
  return http.get(`${API}/workspaces/${WORKSPACE_ID}/extractions/`, () => HttpResponse.json(items));
}

export function extractionDetailHandler(extraction: DocumentExtraction | null) {
  return http.get(`${API}/workspaces/${WORKSPACE_ID}/documents/:documentId/extraction/`, () => {
    if (!extraction) {
      return HttpResponse.json(errorBody('not_found', 'No extraction exists for this document yet.'), {
        status: 404,
      });
    }
    return HttpResponse.json(extraction);
  });
}

export function fieldCorrectionHandler(
  options: { conflict?: boolean } = {},
): ReturnType<typeof http.patch> {
  return http.patch(
    `${API}/workspaces/${WORKSPACE_ID}/documents/:documentId/extraction/fields/:fieldId/`,
    async ({ request, params }) => {
      if (options.conflict) {
        return HttpResponse.json(errorBody('stale_version', 'This extraction was changed by someone else.'), {
          status: 409,
        });
      }
      const body = (await request.json()) as { value: string };
      return HttpResponse.json(
        buildField({ id: params.fieldId as string, display_value: body.value, corrections: [
          { id: 'c-1', before_value: '0.00', after_value: body.value, reason: '', corrected_by_email: 'owner@demo.docpilot.ai', corrected_at: '2026-08-10T00:00:00Z' },
        ] }),
      );
    },
  );
}

/** Stateful pair (GET + PATCH) sharing one in-memory extraction — for
 * the one test that saves a correction and then asserts the refetched
 * extraction reflects it, mirroring what a real backend does (unlike
 * `extractionDetailHandler`, which always serves a fixed snapshot). */
export function statefulExtractionHandlers(initial: DocumentExtraction) {
  let current = initial;
  const get = http.get(`${API}/workspaces/${WORKSPACE_ID}/documents/:documentId/extraction/`, () =>
    HttpResponse.json(current),
  );
  const patch = http.patch(
    `${API}/workspaces/${WORKSPACE_ID}/documents/:documentId/extraction/fields/:fieldId/`,
    async ({ request, params }) => {
      const body = (await request.json()) as { value: string };
      const updatedField = buildField({
        ...current.fields_data.find((f) => f.id === params.fieldId),
        id: params.fieldId as string,
        display_value: body.value,
        normalized_value: body.value,
      });
      current = {
        ...current,
        version: current.version + 1,
        fields_data: current.fields_data.map((f) => (f.id === params.fieldId ? updatedField : f)),
      };
      return HttpResponse.json(updatedField);
    },
  );
  return [get, patch];
}

export function extractionTransitionHandler(
  options: { conflict?: boolean; blocked?: boolean } = {},
) {
  return http.post(
    `${API}/workspaces/${WORKSPACE_ID}/documents/:documentId/extraction/transition/`,
    async ({ request }) => {
      if (options.conflict) {
        return HttpResponse.json(errorBody('stale_version', 'This extraction was changed by someone else.'), {
          status: 409,
        });
      }
      if (options.blocked) {
        return HttpResponse.json(
          errorBody('invalid_transition', 'Cannot approve while unresolved validation errors remain.'),
          { status: 400 },
        );
      }
      const body = (await request.json()) as { status: DocumentExtraction['status'] };
      return HttpResponse.json(buildExtraction({ status: body.status, version: 2 }));
    },
  );
}
