import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { demoWorkspaces } from './handlers';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

function errorBody(code: string, message: string, details: unknown = null) {
  return { error: { code, message, details } };
}

export const demoNotifications = [
  {
    id: 'notif-1',
    event_type: 'approval.requested',
    title: 'Approval requested',
    body: 'Invoice over $10,000 threshold',
    metadata: {},
    is_read: false,
    created_at: '2026-08-10T10:00:05Z',
  },
  {
    id: 'notif-2',
    event_type: 'document.processed',
    title: 'Document processed',
    body: 'acme-invoice-0142.pdf finished processing',
    metadata: {},
    is_read: true,
    created_at: '2026-08-09T09:00:00Z',
  },
];

export const demoWebhookEndpoints = [
  {
    id: 'endpoint-1',
    name: 'CRM sync',
    url: 'https://example.com/hooks/docpilot',
    is_active: true,
    is_simulated: true,
    created_at: '2026-08-01T00:00:00Z',
  },
];

export const demoWebhookDeliveries = [
  {
    id: 'delivery-1',
    event_type: 'document.processed',
    status: 'succeeded' as const,
    response_status_code: 200,
    attempt_count: 1,
    error_code: '',
    created_at: '2026-08-09T09:00:01Z',
    delivered_at: '2026-08-09T09:00:02Z',
  },
];

export const notificationHandlers = [
  http.get(`${API}/workspaces/${WORKSPACE_ID}/notifications/`, () =>
    HttpResponse.json(demoNotifications),
  ),

  http.post(
    `${API}/workspaces/${WORKSPACE_ID}/notifications/:notificationId/read/`,
    ({ params }) => {
      const notification = demoNotifications.find((n) => n.id === params.notificationId);
      if (!notification) {
        return HttpResponse.json(errorBody('not_found', 'Notification not found.'), {
          status: 404,
        });
      }
      notification.is_read = true;
      return HttpResponse.json(notification);
    },
  ),

  http.get(`${API}/workspaces/${WORKSPACE_ID}/integrations/webhooks/`, () =>
    HttpResponse.json(demoWebhookEndpoints),
  ),

  http.post(`${API}/workspaces/${WORKSPACE_ID}/integrations/webhooks/`, async ({ request }) => {
    const body = (await request.json()) as { name: string; url: string; secret: string };
    const endpoint = {
      id: `endpoint-${demoWebhookEndpoints.length + 1}`,
      name: body.name,
      url: body.url,
      is_active: true,
      is_simulated: true,
      created_at: new Date().toISOString(),
    };
    demoWebhookEndpoints.push(endpoint);
    return HttpResponse.json(endpoint, { status: 201 });
  }),

  http.delete(
    `${API}/workspaces/${WORKSPACE_ID}/integrations/webhooks/:endpointId/`,
    ({ params }) => {
      const index = demoWebhookEndpoints.findIndex((e) => e.id === params.endpointId);
      if (index === -1) {
        return HttpResponse.json(errorBody('not_found', 'Webhook endpoint not found.'), {
          status: 404,
        });
      }
      demoWebhookEndpoints.splice(index, 1);
      return new HttpResponse(null, { status: 204 });
    },
  ),

  http.get(`${API}/workspaces/${WORKSPACE_ID}/integrations/webhooks/:endpointId/deliveries/`, () =>
    HttpResponse.json(demoWebhookDeliveries),
  ),
];
