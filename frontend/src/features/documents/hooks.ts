import { useCallback, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ApiError } from '@/lib/apiClient';
import * as documentsApi from './api';
import type { DocumentListParams } from './types';

export const documentsQueryKey = (workspaceId: string | undefined, params?: DocumentListParams) =>
  ['documents', workspaceId, params] as const;

export function useDocuments(workspaceId: string | undefined, params: DocumentListParams) {
  return useQuery({
    queryKey: documentsQueryKey(workspaceId, params),
    queryFn: () => documentsApi.listDocuments(workspaceId!, params),
    enabled: Boolean(workspaceId),
  });
}

export function useDownloadDocument(workspaceId: string | undefined) {
  return useMutation({
    mutationFn: (documentId: string) => documentsApi.getDocument(workspaceId!, documentId),
    onSuccess: (detail) => {
      // Never store the signed URL — open it immediately and let it
      // expire; nothing in this app persists it beyond this callback.
      window.open(detail.download_url, '_blank', 'noopener,noreferrer');
    },
  });
}

export function useArchiveDocument(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => documentsApi.archiveDocument(workspaceId!, documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] });
    },
  });
}

export function useDeleteDocument(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => documentsApi.deleteDocument(workspaceId!, documentId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] });
    },
  });
}

export function useBulkArchiveDocuments(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentIds: string[]) => documentsApi.bulkArchiveDocuments(workspaceId!, documentIds),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] });
    },
  });
}

export function useBulkDeleteDocuments(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentIds: string[]) => documentsApi.bulkDeleteDocuments(workspaceId!, documentIds),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] });
    },
  });
}

export type UploadQueueItemStatus = 'uploading' | 'success' | 'error';

export interface UploadQueueItem {
  id: string;
  file: File;
  status: UploadQueueItemStatus;
  progress: number;
  error?: string;
  controller: AbortController;
}

/**
 * Owns the client-local state of an in-progress multi-file upload —
 * each file gets its own real progress percentage and can be cancelled
 * or retried independently. Intentionally not a `useMutation` (would
 * only track one in-flight request at a time); this composes several
 * concurrent `uploadDocument` calls instead.
 */
export function useDocumentUploadQueue(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  const [items, setItems] = useState<UploadQueueItem[]>([]);

  const updateItem = useCallback((id: string, patch: Partial<UploadQueueItem>) => {
    setItems((current) => current.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }, []);

  const startUpload = useCallback(
    (id: string, file: File) => {
      if (!workspaceId) return;
      const controller = new AbortController();
      updateItem(id, { controller, status: 'uploading', progress: 0, error: undefined });

      documentsApi
        .uploadDocument(workspaceId, file, (progress) => updateItem(id, { progress }), controller.signal)
        .then(() => {
          updateItem(id, { status: 'success', progress: 100 });
          void queryClient.invalidateQueries({ queryKey: ['documents', workspaceId] });
        })
        .catch((error: unknown) => {
          if (error instanceof DOMException && error.name === 'AbortError') {
            setItems((current) => current.filter((item) => item.id !== id));
            return;
          }
          const message = error instanceof ApiError ? error.message : 'Upload failed. Please try again.';
          updateItem(id, { status: 'error', error: message });
        });
    },
    [workspaceId, queryClient, updateItem],
  );

  const addFiles = useCallback(
    (files: File[]) => {
      const newItems: UploadQueueItem[] = files.map((file) => ({
        id: crypto.randomUUID(),
        file,
        status: 'uploading',
        progress: 0,
        controller: new AbortController(),
      }));
      setItems((current) => [...current, ...newItems]);
      newItems.forEach((item) => startUpload(item.id, item.file));
    },
    [startUpload],
  );

  const cancel = useCallback((id: string) => {
    setItems((current) => {
      current.find((item) => item.id === id)?.controller.abort();
      return current;
    });
  }, []);

  const retry = useCallback(
    (id: string) => {
      setItems((current) => {
        const item = current.find((entry) => entry.id === id);
        if (item) startUpload(id, item.file);
        return current;
      });
    },
    [startUpload],
  );

  const remove = useCallback((id: string) => {
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);

  const reset = useCallback(() => setItems([]), []);

  return { items, addFiles, cancel, retry, remove, reset };
}
