import { http, HttpResponse } from 'msw';
import { config } from '@/config';
import { demoWorkspaces } from './handlers';

const API = config.apiBaseUrl;
const WORKSPACE_ID = demoWorkspaces[0]!.id;

export const demoDashboardSummary = {
  total_documents: 12,
  documents_processing: 2,
  documents_needing_review: 3,
  pending_approvals: 1,
  failed_jobs: 0,
};

export const demoAnalyticsOverview = {
  since: '2026-07-14',
  until: '2026-08-12',
  processing_trends: [
    { date: '2026-08-10', total: 3, completed: 3, failed: 0 },
    { date: '2026-08-11', total: 5, completed: 4, failed: 1 },
    { date: '2026-08-12', total: 2, completed: 2, failed: 0 },
  ],
  document_type_counts: [
    { document_type: 'invoice', count: 6 },
    { document_type: 'contract', count: 3 },
  ],
  extraction_accuracy: {
    average_confidence: 0.87,
    total_extractions: 9,
    extractions_with_validation_errors: 2,
    is_illustrative: true,
  },
  review_rate: { total_extractions: 9, reviewed_count: 6, review_rate: 0.6667 },
  workflow_success: { total_runs: 4, succeeded: 3, failed: 1, success_rate: 0.75 },
  approval_duration: { average_duration_seconds: 7200 },
};

export const analyticsHandlers = [
  http.get(`${API}/workspaces/${WORKSPACE_ID}/dashboard/`, () =>
    HttpResponse.json(demoDashboardSummary),
  ),
  http.get(`${API}/workspaces/${WORKSPACE_ID}/analytics/`, () =>
    HttpResponse.json(demoAnalyticsOverview),
  ),
];
