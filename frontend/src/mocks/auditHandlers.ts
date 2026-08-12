import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { demoWorkspaces } from './handlers';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

export const demoAuditEvents = [
  {
    id: 'event-1',
    event_type: 'approval.approved',
    actor_email: 'owner@demo.docpilot.ai',
    metadata: { approval_id: 'approval-2' },
    created_at: '2026-08-09T09:00:00Z',
  },
  {
    id: 'event-2',
    event_type: 'document.uploaded',
    actor_email: 'owner@demo.docpilot.ai',
    metadata: {},
    created_at: '2026-08-08T10:15:00Z',
  },
];

export const auditHandlers = [
  http.get(`${API}/workspaces/${WORKSPACE_ID}/audit-events/`, ({ request }) => {
    const eventType = new URL(request.url).searchParams.get('event_type');
    const results = eventType
      ? demoAuditEvents.filter((e) => e.event_type === eventType)
      : demoAuditEvents;
    return HttpResponse.json({ count: results.length, next: null, previous: null, results });
  }),
];
