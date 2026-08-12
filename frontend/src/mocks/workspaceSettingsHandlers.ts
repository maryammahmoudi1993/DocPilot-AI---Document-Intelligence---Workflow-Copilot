import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { demoWorkspaces } from './handlers';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

export const demoWorkspaceSettings = {
  notify_on_approval_requested: true,
  notify_on_document_processed: true,
  webhook_notifications_enabled: true,
  auto_classify_enabled: true,
  document_retention_days: null as number | null,
  raw_text_retention_days: null as number | null,
  updated_at: '2026-08-01T00:00:00Z',
};

export const workspaceSettingsHandlers = [
  http.get(`${API}/workspaces/${WORKSPACE_ID}/settings/`, () =>
    HttpResponse.json(demoWorkspaceSettings),
  ),
  http.patch(`${API}/workspaces/${WORKSPACE_ID}/settings/`, async ({ request }) => {
    const body = (await request.json()) as Partial<typeof demoWorkspaceSettings>;
    Object.assign(demoWorkspaceSettings, body, { updated_at: new Date().toISOString() });
    return HttpResponse.json(demoWorkspaceSettings);
  }),
];
