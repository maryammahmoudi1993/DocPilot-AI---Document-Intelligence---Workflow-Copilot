import { apiRequest } from '@/lib/apiClient';
import type {
  DocumentExtraction,
  ExtractedField,
  ExtractionQueueItem,
  FieldCorrectionRequest,
  StatusTransitionRequest,
} from './types';

export function getExtractionQueue(workspaceId: string): Promise<ExtractionQueueItem[]> {
  return apiRequest<ExtractionQueueItem[]>(`/workspaces/${workspaceId}/extractions/`);
}

export function getExtraction(workspaceId: string, documentId: string): Promise<DocumentExtraction> {
  return apiRequest<DocumentExtraction>(`/workspaces/${workspaceId}/documents/${documentId}/extraction/`);
}

export function correctField(
  workspaceId: string,
  documentId: string,
  fieldId: string,
  body: FieldCorrectionRequest,
): Promise<ExtractedField> {
  return apiRequest<ExtractedField>(
    `/workspaces/${workspaceId}/documents/${documentId}/extraction/fields/${fieldId}/`,
    { method: 'PATCH', body: JSON.stringify(body) },
  );
}

export function transitionExtraction(
  workspaceId: string,
  documentId: string,
  body: StatusTransitionRequest,
): Promise<DocumentExtraction> {
  return apiRequest<DocumentExtraction>(
    `/workspaces/${workspaceId}/documents/${documentId}/extraction/transition/`,
    { method: 'POST', body: JSON.stringify(body) },
  );
}
