import { config } from '@/config';
import { getAccessToken } from '@/stores/authTokenStore';
import { apiRequest, ApiError, type ApiErrorBody } from '@/lib/apiClient';
import type { DocumentDetail, DocumentListParams, DocumentListResponse, DocumentSummary } from './types';

function buildQuery(params: DocumentListParams): string {
  const query = new URLSearchParams();
  if (params.status) query.set('status', params.status);
  if (params.content_type) query.set('content_type', params.content_type);
  if (params.search) query.set('search', params.search);
  if (params.ordering) query.set('ordering', params.ordering);
  if (params.page) query.set('page', String(params.page));
  if (params.page_size) query.set('page_size', String(params.page_size));
  const qs = query.toString();
  return qs ? `?${qs}` : '';
}

export function listDocuments(workspaceId: string, params: DocumentListParams): Promise<DocumentListResponse> {
  return apiRequest<DocumentListResponse>(`/workspaces/${workspaceId}/documents/${buildQuery(params)}`);
}

export function getDocument(workspaceId: string, documentId: string): Promise<DocumentDetail> {
  return apiRequest<DocumentDetail>(`/workspaces/${workspaceId}/documents/${documentId}/`);
}

export function archiveDocument(workspaceId: string, documentId: string): Promise<DocumentSummary> {
  return apiRequest<DocumentSummary>(`/workspaces/${workspaceId}/documents/${documentId}/archive/`, {
    method: 'POST',
  });
}

export function deleteDocument(workspaceId: string, documentId: string): Promise<void> {
  return apiRequest<void>(`/workspaces/${workspaceId}/documents/${documentId}/`, { method: 'DELETE' });
}

export function bulkArchiveDocuments(workspaceId: string, documentIds: string[]): Promise<DocumentSummary[]> {
  return apiRequest<DocumentSummary[]>(`/workspaces/${workspaceId}/documents/bulk-archive/`, {
    method: 'POST',
    body: JSON.stringify({ document_ids: documentIds }),
  });
}

export function bulkDeleteDocuments(workspaceId: string, documentIds: string[]): Promise<void> {
  return apiRequest<void>(`/workspaces/${workspaceId}/documents/bulk-delete/`, {
    method: 'POST',
    body: JSON.stringify({ document_ids: documentIds }),
  });
}

/**
 * Multipart upload with real (not simulated) progress and cancellation.
 * Deliberately bypasses `apiRequest` — `fetch` has no cross-browser
 * upload-progress event, so this is the one call site in the app that
 * talks to the API with `XMLHttpRequest` directly instead. As a
 * consequence it does not participate in `apiRequest`'s
 * silent-refresh-and-retry: if the access token expires mid-upload the
 * request fails with a 401 surfaced as a normal `ApiError`, rather than
 * transparently retrying after a refresh (see known limitations in the
 * phase completion report).
 */
export function uploadDocument(
  workspaceId: string,
  file: File,
  onProgress?: (percent: number) => void,
  signal?: AbortSignal,
): Promise<DocumentSummary> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${config.apiBaseUrl}/workspaces/${workspaceId}/documents/`, true);
    xhr.withCredentials = true;

    const token = getAccessToken();
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100));
    };

    xhr.onload = () => {
      let body: unknown = null;
      try {
        if (xhr.responseText) body = JSON.parse(xhr.responseText);
      } catch {
        // Non-JSON body (e.g. an upstream proxy error page) — fall through
        // with body left as null so the generic status-based error below applies.
      }

      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body as DocumentSummary);
        return;
      }

      const errorBody = body as ApiErrorBody | null;
      if (errorBody?.error) {
        reject(new ApiError(xhr.status, errorBody));
      } else {
        reject(new Error(`Upload failed with status ${xhr.status}`));
      }
    };

    xhr.onerror = () => reject(new Error('Upload failed due to a network error.'));
    xhr.onabort = () => reject(new DOMException('Upload cancelled', 'AbortError'));

    if (signal) {
      if (signal.aborted) {
        xhr.abort();
      } else {
        signal.addEventListener('abort', () => xhr.abort());
      }
    }

    const formData = new FormData();
    formData.append('file', file);
    xhr.send(formData);
  });
}
