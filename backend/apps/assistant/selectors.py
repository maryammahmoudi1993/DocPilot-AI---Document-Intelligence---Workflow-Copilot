from django.db.models import QuerySet

from apps.assistant.models import Conversation


def get_workspace_conversations(*, workspace_id: str) -> QuerySet[Conversation]:
    return Conversation.objects.filter(workspace_id=workspace_id).order_by("-updated_at")


def get_workspace_conversation(*, workspace_id: str, conversation_id: str) -> Conversation | None:
    return (
        Conversation.objects.filter(workspace_id=workspace_id, id=conversation_id)
        .prefetch_related("messages", "messages__citations", "messages__usage")
        .first()
    )
