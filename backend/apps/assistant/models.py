"""RAG knowledge assistant models — pgvector-indexed document chunks,
conversations, messages, and answer citations. Enabling pgvector itself
happens in this app's first migration (`VectorExtension`), since this is
the app that introduces the first vector column in the project."""

import uuid

from django.conf import settings
from django.db import models
from pgvector.django import VectorField

EMBEDDING_DIMENSIONS = settings.RAG_EMBEDDING_DIMENSIONS


class DocumentChunk(models.Model):
    """One indexed slice of one document's text, with its embedding.
    Created by apps.processing's INDEXING stage (see
    apps/assistant/services.index_document) — never edited by a human,
    unlike apps.extraction's fields. Re-indexing a document deletes and
    recreates its chunks rather than diffing them, which is what makes
    indexing idempotent (see services.index_document's docstring)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        "documents.Document", on_delete=models.CASCADE, related_name="chunks"
    )
    # Denormalized from document.workspace — see ProcessingJob.workspace
    # for the same rationale. This is what makes retrieval's workspace
    # filter a single indexed column rather than a join.
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="document_chunks"
    )
    chunk_index = models.PositiveIntegerField()
    page_number = models.PositiveIntegerField()
    # Free-text section label when the chunking strategy can identify one
    # (not attempted in this phase's simple fixed-size chunker — always
    # blank for now, but modeled so a smarter chunker can populate it
    # later without a schema change).
    section = models.CharField(max_length=255, blank=True)
    text = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "document"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"], name="unique_chunk_per_document"
            )
        ]
        ordering = ["document", "chunk_index"]

    def __str__(self) -> str:
        return f"DocumentChunk({self.document_id}, {self.chunk_index})"


class Conversation(models.Model):
    """One assistant conversation thread, scoped to a workspace and
    (optionally) a subset of that workspace's documents."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace", on_delete=models.CASCADE, related_name="conversations"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    title = models.CharField(max_length=255, blank=True)
    # Document IDs (as strings) this conversation is scoped to; an empty
    # list means "search every document in the workspace". Validated
    # against real workspace membership at question time (see
    # services.answer_question) — never trusted as-is for retrieval.
    document_scope = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["workspace", "-updated_at"])]
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"Conversation({self.id})"


class MessageRole(models.TextChoices):
    USER = "user", "User"
    ASSISTANT = "assistant", "Assistant"


class Message(models.Model):
    """One turn in a conversation. `content` for a user message is the
    literal question; for an assistant message it's the generated
    answer — both are legitimately part of the conversation record, not
    the "sensitive content" the no-logging rule is about (that rule
    targets provider prompts/raw document text — see ModelUsageRecord)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    role = models.CharField(max_length=16, choices=MessageRole.choices)
    content = models.TextField()
    # True when the assistant declined to answer because grounding was
    # too weak — see services.answer_question. `content` is still a
    # short, honest "insufficient evidence" message in that case, never
    # a fabricated answer.
    is_insufficient_evidence = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["conversation", "created_at"])]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Message({self.conversation_id}, {self.role})"


class AnswerCitation(models.Model):
    """One citation on an assistant Message, pointing at the exact chunk
    (and therefore document + page) the cited snippet came from."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="citations")
    chunk = models.ForeignKey(DocumentChunk, on_delete=models.CASCADE, related_name="citations")
    # Short quoted excerpt only — bounded so a citation can never become
    # a backdoor for re-surfacing an entire chunk's text beyond what the
    # cited snippet actually needs to show.
    snippet = models.CharField(max_length=500)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=["message", "order"])]
        ordering = ["order"]

    def __str__(self) -> str:
        return f"AnswerCitation({self.message_id}, chunk={self.chunk_id})"


class ModelUsageRecord(models.Model):
    """Usage accounting for one generation call — counts and timing
    only. Never the prompt, the retrieved context, or the generated
    text; those already live safely on Message/DocumentChunk where
    appropriate, or (for the assembled prompt) nowhere at all."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.OneToOneField(Message, on_delete=models.CASCADE, related_name="usage")
    provider = models.CharField(max_length=32)
    prompt_tokens = models.PositiveIntegerField()
    completion_tokens = models.PositiveIntegerField()
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"ModelUsageRecord({self.message_id}, {self.provider})"
