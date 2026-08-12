import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import type { ApprovalRequest } from '@/features/approvals/types';
import { demoWorkspaces } from './handlers';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

function errorBody(code: string, message: string, details: unknown = null) {
  return { error: { code, message, details } };
}

/** Fixtures matching the real backend contract (apps.approvals
 * serializers). One mutable array (reset in beforeEach by tests that
 * import it) so decide()/comment mutations are visible on refetch,
 * mirroring how the real API behaves. */
export const demoApprovals: ApprovalRequest[] = [
  {
    id: 'approval-1',
    title: 'Invoice over $10,000 threshold',
    description: 'Vendor invoice exceeds the auto-approval limit.',
    risk_level: 'high' as const,
    status: 'pending' as const,
    assigned_role: 'admin',
    document_id: 'doc-1',
    requested_by_email: 'owner@demo.docpilot.ai',
    decided_by_email: null,
    decided_at: null,
    expires_at: null,
    comments: [],
    created_at: '2026-08-10T10:00:00Z',
    updated_at: '2026-08-10T10:00:00Z',
  },
  {
    id: 'approval-2',
    title: 'Contract renewal — Acme Corp',
    description: '',
    risk_level: 'medium' as const,
    status: 'approved' as const,
    assigned_role: 'admin',
    document_id: null,
    requested_by_email: 'owner@demo.docpilot.ai',
    decided_by_email: 'owner@demo.docpilot.ai',
    decided_at: '2026-08-09T09:00:00Z',
    expires_at: null,
    comments: [
      {
        id: 'comment-1',
        author_email: 'owner@demo.docpilot.ai',
        body: 'Looks good.',
        created_at: '2026-08-09T08:55:00Z',
      },
    ],
    created_at: '2026-08-08T10:00:00Z',
    updated_at: '2026-08-09T09:00:00Z',
  },
];

export const approvalHandlers = [
  http.get(`${API}/workspaces/${WORKSPACE_ID}/approvals/`, ({ request }) => {
    const status = new URL(request.url).searchParams.get('status');
    const results = status ? demoApprovals.filter((a) => a.status === status) : demoApprovals;
    return HttpResponse.json(results);
  }),

  http.get(`${API}/workspaces/${WORKSPACE_ID}/approvals/:approvalId/`, ({ params }) => {
    const approval = demoApprovals.find((a) => a.id === params.approvalId);
    if (!approval) {
      return HttpResponse.json(errorBody('not_found', 'Approval request not found.'), {
        status: 404,
      });
    }
    return HttpResponse.json(approval);
  }),

  http.post(
    `${API}/workspaces/${WORKSPACE_ID}/approvals/:approvalId/decide/`,
    async ({ params, request }) => {
      const approval = demoApprovals.find((a) => a.id === params.approvalId);
      if (!approval) {
        return HttpResponse.json(errorBody('not_found', 'Approval request not found.'), {
          status: 404,
        });
      }
      const body = (await request.json()) as { status: 'approved' | 'rejected'; reason?: string };
      approval.status = body.status;
      approval.decided_by_email = 'owner@demo.docpilot.ai';
      approval.decided_at = new Date().toISOString();
      if (body.reason) {
        approval.comments = [
          ...approval.comments,
          {
            id: `comment-${approval.comments.length + 1}`,
            author_email: 'owner@demo.docpilot.ai',
            body: body.reason,
            created_at: new Date().toISOString(),
          },
        ];
      }
      return HttpResponse.json(approval);
    },
  ),

  http.post(
    `${API}/workspaces/${WORKSPACE_ID}/approvals/:approvalId/comments/`,
    async ({ params, request }) => {
      const approval = demoApprovals.find((a) => a.id === params.approvalId);
      if (!approval) {
        return HttpResponse.json(errorBody('not_found', 'Approval request not found.'), {
          status: 404,
        });
      }
      const body = (await request.json()) as { body: string };
      const comment = {
        id: `comment-${approval.comments.length + 1}`,
        author_email: 'owner@demo.docpilot.ai',
        body: body.body,
        created_at: new Date().toISOString(),
      };
      approval.comments = [...approval.comments, comment];
      return HttpResponse.json(comment, { status: 201 });
    },
  ),
];
