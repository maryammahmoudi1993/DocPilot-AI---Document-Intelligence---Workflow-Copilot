import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as notificationsApi from './api';
import type { WebhookEndpointCreateRequest } from './types';

export const notificationsQueryKey = (workspaceId: string | undefined) =>
  ['notifications', workspaceId] as const;

export const webhookEndpointsQueryKey = (workspaceId: string | undefined) =>
  ['webhook-endpoints', workspaceId] as const;

export const webhookDeliveriesQueryKey = (
  workspaceId: string | undefined,
  endpointId: string | undefined,
) => ['webhook-deliveries', workspaceId, endpointId] as const;

/** Polls at a fixed, modest interval — the bell icon's unread count only
 * needs to be "eventually accurate", not push-real-time; a plain
 * refetchInterval avoids adding a websocket/SSE dependency for a
 * portfolio-scale project. */
export function useNotifications(workspaceId: string | undefined) {
  return useQuery({
    queryKey: notificationsQueryKey(workspaceId),
    queryFn: () => notificationsApi.listNotifications(workspaceId!),
    enabled: Boolean(workspaceId),
    refetchInterval: 30_000,
  });
}

export function useMarkNotificationRead(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) =>
      notificationsApi.markNotificationRead(workspaceId!, notificationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: notificationsQueryKey(workspaceId) });
    },
  });
}

export function useWebhookEndpoints(workspaceId: string | undefined) {
  return useQuery({
    queryKey: webhookEndpointsQueryKey(workspaceId),
    queryFn: () => notificationsApi.listWebhookEndpoints(workspaceId!),
    enabled: Boolean(workspaceId),
  });
}

export function useCreateWebhookEndpoint(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: WebhookEndpointCreateRequest) =>
      notificationsApi.createWebhookEndpoint(workspaceId!, body),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: webhookEndpointsQueryKey(workspaceId) });
    },
  });
}

export function useDeleteWebhookEndpoint(workspaceId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (endpointId: string) =>
      notificationsApi.deleteWebhookEndpoint(workspaceId!, endpointId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: webhookEndpointsQueryKey(workspaceId) });
    },
  });
}

export function useWebhookDeliveries(
  workspaceId: string | undefined,
  endpointId: string | undefined,
) {
  return useQuery({
    queryKey: webhookDeliveriesQueryKey(workspaceId, endpointId),
    queryFn: () => notificationsApi.listWebhookDeliveries(workspaceId!, endpointId!),
    enabled: Boolean(workspaceId && endpointId),
  });
}
