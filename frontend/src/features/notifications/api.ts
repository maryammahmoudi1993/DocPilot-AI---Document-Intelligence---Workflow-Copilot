import { apiRequest } from '@/lib/apiClient';
import type {
  Notification,
  WebhookDelivery,
  WebhookEndpoint,
  WebhookEndpointCreateRequest,
} from './types';

export function listNotifications(workspaceId: string): Promise<Notification[]> {
  return apiRequest<Notification[]>(`/workspaces/${workspaceId}/notifications/`);
}

export function markNotificationRead(
  workspaceId: string,
  notificationId: string,
): Promise<Notification> {
  return apiRequest<Notification>(
    `/workspaces/${workspaceId}/notifications/${notificationId}/read/`,
    { method: 'POST' },
  );
}

export function listWebhookEndpoints(workspaceId: string): Promise<WebhookEndpoint[]> {
  return apiRequest<WebhookEndpoint[]>(`/workspaces/${workspaceId}/integrations/webhooks/`);
}

export function createWebhookEndpoint(
  workspaceId: string,
  body: WebhookEndpointCreateRequest,
): Promise<WebhookEndpoint> {
  return apiRequest<WebhookEndpoint>(`/workspaces/${workspaceId}/integrations/webhooks/`, {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export function deleteWebhookEndpoint(workspaceId: string, endpointId: string): Promise<void> {
  return apiRequest<void>(`/workspaces/${workspaceId}/integrations/webhooks/${endpointId}/`, {
    method: 'DELETE',
  });
}

export function listWebhookDeliveries(
  workspaceId: string,
  endpointId: string,
): Promise<WebhookDelivery[]> {
  return apiRequest<WebhookDelivery[]>(
    `/workspaces/${workspaceId}/integrations/webhooks/${endpointId}/deliveries/`,
  );
}
