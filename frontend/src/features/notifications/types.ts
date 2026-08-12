export interface Notification {
  id: string;
  event_type: string;
  title: string;
  body: string;
  metadata: Record<string, unknown>;
  is_read: boolean;
  created_at: string;
}

export type WebhookDeliveryStatus = 'pending' | 'succeeded' | 'failed';

export interface WebhookDelivery {
  id: string;
  event_type: string;
  status: WebhookDeliveryStatus;
  response_status_code: number | null;
  attempt_count: number;
  error_code: string;
  created_at: string;
  delivered_at: string | null;
}

export interface WebhookEndpoint {
  id: string;
  name: string;
  url: string;
  is_active: boolean;
  is_simulated: boolean;
  created_at: string;
}

export interface WebhookEndpointCreateRequest {
  name: string;
  url: string;
  secret: string;
}
