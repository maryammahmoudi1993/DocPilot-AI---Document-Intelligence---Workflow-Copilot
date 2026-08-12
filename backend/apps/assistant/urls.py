from django.urls import path

from apps.assistant.views import (
    ConversationDetailView,
    ConversationListCreateView,
    MessageCreateView,
)

urlpatterns = [
    path("", ConversationListCreateView.as_view(), name="assistant-conversation-list"),
    path(
        "<uuid:conversation_id>/",
        ConversationDetailView.as_view(),
        name="assistant-conversation-detail",
    ),
    path(
        "<uuid:conversation_id>/messages/",
        MessageCreateView.as_view(),
        name="assistant-conversation-messages",
    ),
]
