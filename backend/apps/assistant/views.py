from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.assistant import services
from apps.assistant.exceptions import InvalidDocumentScopeAPIError
from apps.assistant.models import Message
from apps.assistant.providers import get_embedding_provider, get_generation_provider
from apps.assistant.selectors import get_workspace_conversation, get_workspace_conversations
from apps.assistant.serializers import (
    AskQuestionRequestSerializer,
    ConversationCreateRequestSerializer,
    ConversationDetailSerializer,
    ConversationSerializer,
    MessageSerializer,
)
from apps.assistant.services import InvalidDocumentScopeError
from apps.workspaces.models import Workspace
from apps.workspaces.permissions import IsWorkspaceMember


class ConversationListCreateView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=ConversationSerializer(many=True))
    def get(self, request: Request, workspace_id: str) -> Response:
        conversations = get_workspace_conversations(workspace_id=workspace_id)
        return Response(ConversationSerializer(conversations, many=True).data)

    @extend_schema(
        request=ConversationCreateRequestSerializer, responses=ConversationDetailSerializer
    )
    def post(self, request: Request, workspace_id: str) -> Response:
        workspace = get_object_or_404(Workspace, id=workspace_id)
        payload = ConversationCreateRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        try:
            conversation = services.create_conversation(
                workspace=workspace,
                user=request.user,
                document_scope=[str(v) for v in payload.validated_data["document_scope"]],
            )
        except InvalidDocumentScopeError as exc:
            raise InvalidDocumentScopeAPIError() from exc

        return Response(ConversationDetailSerializer(conversation).data, status=201)


class ConversationDetailView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(responses=ConversationDetailSerializer)
    def get(self, request: Request, workspace_id: str, conversation_id: str) -> Response:
        conversation = get_workspace_conversation(
            workspace_id=workspace_id, conversation_id=conversation_id
        )
        if conversation is None:
            raise NotFound("Conversation not found.")
        return Response(ConversationDetailSerializer(conversation).data)


class MessageCreateView(APIView):
    permission_classes = [IsWorkspaceMember]

    @extend_schema(request=AskQuestionRequestSerializer, responses=MessageSerializer)
    def post(self, request: Request, workspace_id: str, conversation_id: str) -> Response:
        conversation = get_workspace_conversation(
            workspace_id=workspace_id, conversation_id=conversation_id
        )
        if conversation is None:
            raise NotFound("Conversation not found.")

        payload = AskQuestionRequestSerializer(data=request.data)
        payload.is_valid(raise_exception=True)

        assistant_message: Message = services.answer_question(
            conversation=conversation,
            question=payload.validated_data["question"],
            embedding_provider=get_embedding_provider(),
            generation_provider=get_generation_provider(),
        )
        return Response(MessageSerializer(assistant_message).data, status=201)
