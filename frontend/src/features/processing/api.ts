import { apiRequest } from '@/lib/apiClient';
import type { ProcessingJob } from './types';

export function getProcessingStatus(workspaceId: string, documentId: string): Promise<ProcessingJob> {
  return apiRequest<ProcessingJob>(`/workspaces/${workspaceId}/documents/${documentId}/processing/`);
}

export function retryProcessing(workspaceId: string, documentId: string): Promise<ProcessingJob> {
  return apiRequest<ProcessingJob>(`/workspaces/${workspaceId}/documents/${documentId}/processing/retry/`, {
    method: 'POST',
  });
}
