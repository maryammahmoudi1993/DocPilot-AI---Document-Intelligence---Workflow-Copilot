from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification, WebhookDelivery, WebhookEndpoint
from apps.notifications.serializers import (
    NotificationSerializer,
    WebhookDeliverySerializer,
    WebhookEndpointCreateRequestSerializer,
    WebhookEndpointSerializer,
)
from apps.notifications.services import create_webhook_endpoint, get_user_notifications
from apps.workspaces.models import Role, Workspace
from apps.workspaces.permissions import IsWorkspaceMember, get_workspace_membership

_CAN_MANAGE_INTEGRATIONS_ROLES = {Role.OWNER, Role.ADMIN}


class NotificationListView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=NotificationSerializer(many=True))
    def get(self, request: Request, workspace_id: str) -> Response:
        notifications = get_user_notifications(workspace_id=workspace_id, user=request.user)
        return Response(NotificationSerializer(notifications, many=True).data)


class NotificationMarkReadView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=None, responses=NotificationSerializer)
    def post(self, request: Request, workspace_id: str, notification_id: str) -> Response:
        notification = get_object_or_404(
            Notification, id=notification_id, workspace_id=workspace_id, user=request.user
        )
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class WebhookEndpointListCreateView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=WebhookEndpointSerializer(many=True))
    def get(self, request: Request, workspace_id: str) -> Response:
        endpoints = WebhookEndpoint.objects.filter(workspace_id=workspace_id)
        return Response(WebhookEndpointSerializer(endpoints, many=True).data)

    @extend_schema(
        request=WebhookEndpointCreateRequestSerializer, responses=WebhookEndpointSerializer
    )
    def post(self, request: Request, workspace_id: str) -> Response:
        if get_workspace_membership(request).role not in _CAN_MANAGE_INTEGRATIONS_ROLES:
            raise PermissionDenied("You do not have permission to manage integrations.")

        workspace = get_object_or_404(Workspace, id=workspace_id)
        payload = WebhookEndpointCreateRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        endpoint = create_webhook_endpoint(
            workspace=workspace,
            user=request.user,
            name=payload.validated_data["name"],
            url=payload.validated_data["url"],
            secret=payload.validated_data["secret"],
        )
        return Response(WebhookEndpointSerializer(endpoint).data, status=201)


class WebhookEndpointDetailView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=None, responses={204: None})
    def delete(self, request: Request, workspace_id: str, endpoint_id: str) -> Response:
        if get_workspace_membership(request).role not in _CAN_MANAGE_INTEGRATIONS_ROLES:
            raise PermissionDenied("You do not have permission to manage integrations.")

        endpoint = get_object_or_404(WebhookEndpoint, id=endpoint_id, workspace_id=workspace_id)
        endpoint.delete()
        return Response(status=204)


class WebhookDeliveryListView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=WebhookDeliverySerializer(many=True))
    def get(self, request: Request, workspace_id: str, endpoint_id: str) -> Response:
        endpoint = WebhookEndpoint.objects.filter(id=endpoint_id, workspace_id=workspace_id).first()
        if endpoint is None:
            raise NotFound("Webhook endpoint not found.")
        deliveries = WebhookDelivery.objects.filter(endpoint=endpoint)
        return Response(WebhookDeliverySerializer(deliveries, many=True).data)
