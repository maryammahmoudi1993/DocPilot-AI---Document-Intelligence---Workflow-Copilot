export interface AuditEvent {
  id: string;
  event_type: string;
  actor_email: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface AuditEventPage {
  count: number;
  next: string | null;
  previous: string | null;
  results: AuditEvent[];
}

export interface AuditEventFilters {
  event_type?: string;
  since?: string;
  until?: string;
  page?: number;
}
