from rest_framework import serializers

from apps.assistant.models import AnswerCitation, Conversation, Message

VALID_DOCUMENT_SCOPE_MAX = 50


class AnswerCitationSerializer(serializers.ModelSerializer):
    document_id = serializers.UUIDField(source="chunk.document_id", read_only=True)
    filename = serializers.CharField(source="chunk.document.filename", read_only=True)
    page_number = serializers.IntegerField(source="chunk.page_number", read_only=True)

    class Meta:
        model = AnswerCitation
        fields = ["id", "document_id", "filename", "page_number", "snippet", "order"]
        read_only_fields = fields


class MessageSerializer(serializers.ModelSerializer):
    citations = AnswerCitationSerializer(many=True, read_only=True)

    class Meta:
        model = Message
        fields = ["id", "role", "content", "is_insufficient_evidence", "citations", "created_at"]
        read_only_fields = fields


class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ["id", "title", "document_scope", "created_at", "updated_at"]
        read_only_fields = fields


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "title", "document_scope", "messages", "created_at", "updated_at"]
        read_only_fields = fields


class ConversationCreateRequestSerializer(serializers.Serializer):
    document_scope = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
        max_length=VALID_DOCUMENT_SCOPE_MAX,
    )


class AskQuestionRequestSerializer(serializers.Serializer):
    question = serializers.CharField(min_length=1, max_length=2000)
