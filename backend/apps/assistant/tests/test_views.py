import pytest
from django.urls import reverse

from apps.assistant import services
from apps.assistant.providers import MockEmbeddingProvider
from apps.workspaces.models import Role
from tests.factories import (
    ConversationFactory,
    DocumentFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.fixture
def workspace():
    return WorkspaceFactory()


def _client_with_role(api_client, workspace, role=Role.VIEWER):
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace, role=role)
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.mark.django_db
class TestConversationListCreateView:
    def test_creates_a_conversation(self, api_client, workspace):
        _client_with_role(api_client, workspace)

        response = api_client.post(
            reverse("assistant-conversation-list", args=[workspace.id]),
            {"document_scope": []},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["document_scope"] == []

    def test_rejects_a_document_scope_id_from_another_workspace(self, api_client, workspace):
        other_doc = DocumentFactory()
        _client_with_role(api_client, workspace)

        response = api_client.post(
            reverse("assistant-conversation-list", args=[workspace.id]),
            {"document_scope": [str(other_doc.id)]},
            format="json",
        )

        assert response.status_code == 400
        assert response.data["error"]["code"] == "invalid_document_scope"

    def test_lists_the_workspaces_conversations(self, api_client, workspace):
        ConversationFactory(workspace=workspace)
        _client_with_role(api_client, workspace)

        response = api_client.get(reverse("assistant-conversation-list", args=[workspace.id]))

        assert response.status_code == 200
        assert len(response.data) == 1

    def test_anonymous_is_rejected(self, api_client, workspace):
        response = api_client.get(reverse("assistant-conversation-list", args=[workspace.id]))

        assert response.status_code == 401


@pytest.mark.django_db
class TestConversationDetailView:
    def test_returns_messages_and_citations(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        embedding_provider = MockEmbeddingProvider(dimensions=256)
        services.index_document(
            document, page_texts=[(1, "Total due: $1200.")], provider=embedding_provider
        )
        conversation = ConversationFactory(workspace=workspace)
        from apps.assistant.providers import MockGenerationProvider

        services.answer_question(
            conversation=conversation,
            question="What is the total?",
            embedding_provider=embedding_provider,
            generation_provider=MockGenerationProvider(),
        )
        _client_with_role(api_client, workspace)

        response = api_client.get(
            reverse("assistant-conversation-detail", args=[workspace.id, conversation.id])
        )

        assert response.status_code == 200
        assert len(response.data["messages"]) == 2

    def test_another_workspaces_conversation_is_not_visible(self, api_client, workspace):
        other_conversation = ConversationFactory()
        _client_with_role(api_client, workspace)

        response = api_client.get(
            reverse("assistant-conversation-detail", args=[workspace.id, other_conversation.id])
        )

        assert response.status_code == 404


@pytest.mark.django_db
class TestMessageCreateView:
    def test_asks_a_question_and_returns_the_assistant_message(self, api_client, workspace):
        document = DocumentFactory(workspace=workspace)
        embedding_provider = MockEmbeddingProvider(dimensions=256)
        services.index_document(
            document, page_texts=[(1, "Total due: $1200.")], provider=embedding_provider
        )
        conversation = ConversationFactory(workspace=workspace)
        _client_with_role(api_client, workspace)

        response = api_client.post(
            reverse("assistant-conversation-messages", args=[workspace.id, conversation.id]),
            {"question": "What is the total?"},
            format="json",
        )

        assert response.status_code == 201
        assert response.data["role"] == "assistant"

    def test_blank_question_is_rejected(self, api_client, workspace):
        conversation = ConversationFactory(workspace=workspace)
        _client_with_role(api_client, workspace)

        response = api_client.post(
            reverse("assistant-conversation-messages", args=[workspace.id, conversation.id]),
            {"question": ""},
            format="json",
        )

        assert response.status_code == 400

    def test_conversation_from_another_workspace_returns_404(self, api_client, workspace):
        other_conversation = ConversationFactory()
        _client_with_role(api_client, workspace)

        response = api_client.post(
            reverse("assistant-conversation-messages", args=[workspace.id, other_conversation.id]),
            {"question": "anything"},
            format="json",
        )

        assert response.status_code == 404

    def test_anonymous_cannot_ask(self, api_client, workspace):
        conversation = ConversationFactory(workspace=workspace)

        response = api_client.post(
            reverse("assistant-conversation-messages", args=[workspace.id, conversation.id]),
            {"question": "anything"},
            format="json",
        )

        assert response.status_code == 401
