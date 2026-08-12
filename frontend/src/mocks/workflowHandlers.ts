import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import type {
  Workflow,
  WorkflowDetail,
  WorkflowRun,
  WorkflowVersionWithValidation,
} from '@/features/workflows/types';
import { demoWorkspaces } from './handlers';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

function errorBody(code: string, message: string, details: unknown = null) {
  return { error: { code, message, details } };
}

export function buildWorkflow(overrides: Partial<Workflow> = {}): Workflow {
  return {
    id: 'wf-1',
    name: 'Invoice approval',
    is_active: false,
    created_at: '2026-08-12T00:00:00Z',
    updated_at: '2026-08-12T00:00:00Z',
    ...overrides,
  };
}

export function buildVersion(
  overrides: Partial<WorkflowVersionWithValidation> = {},
): WorkflowVersionWithValidation {
  return {
    id: 'ver-1',
    version_number: 1,
    status: 'draft',
    nodes: [],
    edges: [],
    created_at: '2026-08-12T00:00:00Z',
    activated_at: null,
    ...overrides,
  };
}

export function buildWorkflowDetail(overrides: Partial<WorkflowDetail> = {}): WorkflowDetail {
  return {
    ...buildWorkflow(),
    active_version: null,
    draft_version: buildVersion(),
    ...overrides,
  };
}

export function workflowListHandler(workflows: Workflow[]) {
  return http.get(`${API}/workspaces/${WORKSPACE_ID}/workflows/`, () => HttpResponse.json(workflows));
}

export function createWorkflowHandler(detail: WorkflowDetail) {
  return http.post(`${API}/workspaces/${WORKSPACE_ID}/workflows/`, () =>
    HttpResponse.json(detail, { status: 201 }),
  );
}

export function workflowDetailHandler(detail: WorkflowDetail) {
  return http.get(`${API}/workspaces/${WORKSPACE_ID}/workflows/:workflowId/`, () =>
    HttpResponse.json(detail),
  );
}

export function saveDraftHandler(
  version: WorkflowVersionWithValidation,
  options: { validationErrors?: string[] } = {},
) {
  return http.put(`${API}/workspaces/${WORKSPACE_ID}/workflows/:workflowId/draft/`, async ({ request }) => {
    const body = (await request.json()) as { nodes: unknown[]; edges: unknown[] };
    return HttpResponse.json({
      ...version,
      nodes: body.nodes,
      edges: body.edges,
      validation_errors: options.validationErrors ?? [],
    });
  });
}

export function activateWorkflowHandler(
  options: { error?: string } = {},
): ReturnType<typeof http.post> {
  return http.post(`${API}/workspaces/${WORKSPACE_ID}/workflows/:workflowId/activate/`, () => {
    if (options.error) {
      return HttpResponse.json(errorBody('invalid_graph', options.error), { status: 400 });
    }
    return HttpResponse.json(buildVersion({ status: 'active' }));
  });
}

export function deactivateWorkflowHandler() {
  return http.post(`${API}/workspaces/${WORKSPACE_ID}/workflows/:workflowId/deactivate/`, () =>
    HttpResponse.json(buildWorkflow({ is_active: false })),
  );
}

export function testRunHandler(run: WorkflowRun) {
  return http.post(`${API}/workspaces/${WORKSPACE_ID}/workflows/:workflowId/test-run/`, () =>
    HttpResponse.json(run, { status: 201 }),
  );
}

export function workflowRunsHandler(runs: WorkflowRun[]) {
  return http.get(`${API}/workspaces/${WORKSPACE_ID}/workflows/:workflowId/runs/`, () =>
    HttpResponse.json(runs),
  );
}
