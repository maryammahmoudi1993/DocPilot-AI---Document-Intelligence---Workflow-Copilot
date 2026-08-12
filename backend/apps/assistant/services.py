"""Business logic for chunking/indexing, workspace-filtered retrieval,
and grounded answer generation — kept out of views/tasks per the
project's non-negotiable rule. Three entry points matter most:

- `index_document` — called from the processing pipeline's INDEXING
  stage; idempotent (see its docstring).
- `retrieve_chunks` — workspace- and (optionally) document-scope-filtered
  vector search.
- `answer_question` — retrieval + grounding decision + generation +
  citation persistence, wrapped in one transaction.
"""

import time
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction
from pgvector.django import CosineDistance

from apps.assistant.exceptions import ProviderUnavailableAPIError
from apps.assistant.models import (
    AnswerCitation,
    Conversation,
    DocumentChunk,
    Message,
    MessageRole,
    ModelUsageRecord,
)
from apps.assistant.providers import (
    ContextChunk,
    EmbeddingProvider,
    GenerationProvider,
    ProviderUnavailableError,
)


class InvalidDocumentScopeError(Exception):
    """Raised when a conversation's requested document_scope includes an
    id that doesn't exist in this workspace — never trusted as-is (see
    retrieve_chunks' docstring), but also rejected outright at creation
    time rather than silently dropped, so the caller learns immediately
    rather than getting confusing empty results later."""


@transaction.atomic
def create_conversation(
    *, workspace, user, document_scope: list[str] | None = None
) -> Conversation:
    from apps.documents.models import Document

    scope = document_scope or []
    if scope:
        real_count = Document.objects.filter(workspace=workspace, id__in=scope).count()
        if real_count != len(set(scope)):
            raise InvalidDocumentScopeError()

    return Conversation.objects.create(workspace=workspace, created_by=user, document_scope=scope)


@dataclass(frozen=True)
class ChunkSpan:
    page_number: int
    text: str


def chunk_pages(
    page_texts: list[tuple[int, str]], *, chunk_size: int | None = None
) -> list[ChunkSpan]:
    """Fixed-size character chunking within each page — simple and
    deterministic (same input always yields the same chunks, required
    for idempotent indexing and the deterministic RAG test set). Chunks
    never span a page boundary, which is what keeps every chunk's page
    number — and therefore every citation's page number — exact."""
    size = chunk_size or settings.RAG_CHUNK_SIZE_CHARS
    spans: list[ChunkSpan] = []
    for page_number, text in page_texts:
        words = text.split()
        current: list[str] = []
        current_len = 0
        for word in words:
            if current and current_len + len(word) + 1 > size:
                spans.append(ChunkSpan(page_number=page_number, text=" ".join(current)))
                current, current_len = [], 0
            current.append(word)
            current_len += len(word) + 1
        if current:
            spans.append(ChunkSpan(page_number=page_number, text=" ".join(current)))
    return spans


@transaction.atomic
def index_document(
    document, *, page_texts: list[tuple[int, str]], provider: EmbeddingProvider
) -> list[DocumentChunk]:
    """(Re)builds every chunk for `document` from scratch. Idempotent:
    unlike apps.extraction (which preserves human corrections), chunks
    are never human-edited, so unconditionally deleting and recreating
    them from the same input text is always safe — a duplicate/retried
    indexing task run just produces the same chunks again."""
    DocumentChunk.objects.filter(document=document).delete()
    spans = chunk_pages(page_texts)
    chunks = [
        DocumentChunk(
            document=document,
            workspace_id=document.workspace_id,
            chunk_index=index,
            page_number=span.page_number,
            text=span.text,
            embedding=provider.embed(text=span.text),
        )
        for index, span in enumerate(spans)
    ]
    return DocumentChunk.objects.bulk_create(chunks)


def retrieve_chunks(
    *,
    workspace_id: str,
    query_embedding: list[float],
    document_ids: list[str] | None = None,
    top_k: int | None = None,
) -> list[tuple[DocumentChunk, float]]:
    """Workspace-scoped vector search — `workspace_id` is never
    optional, and `document_ids` (when given) is intersected with it
    rather than trusted on its own, so a scope list from another
    workspace can never leak a cross-workspace chunk into results (see
    the corresponding isolation test)."""
    queryset = DocumentChunk.objects.filter(workspace_id=workspace_id)
    if document_ids:
        queryset = queryset.filter(document_id__in=document_ids)
    queryset = queryset.annotate(distance=CosineDistance("embedding", query_embedding)).order_by(
        "distance"
    )[: top_k or settings.RAG_RETRIEVAL_TOP_K]
    return [(chunk, chunk.distance) for chunk in queryset]


def build_context(
    ranked_chunks: list[tuple[DocumentChunk, float]], *, budget_chars: int | None = None
) -> list[ContextChunk]:
    """Trims retrieved chunks to a documented character budget before
    they're handed to the generation provider — the token-budget
    enforcement this phase requires. Chunks are already ranked
    best-first; this only ever drops the *tail* (weakest matches), never
    reorders."""
    budget = budget_chars or settings.RAG_CONTEXT_BUDGET_CHARS
    context: list[ContextChunk] = []
    used = 0
    for chunk, distance in ranked_chunks:
        if used + len(chunk.text) > budget and context:
            break
        context.append(
            ContextChunk(
                chunk_id=str(chunk.id),
                document_id=str(chunk.document_id),
                filename=chunk.document.filename,
                page_number=chunk.page_number,
                text=chunk.text,
                distance=distance,
            )
        )
        used += len(chunk.text)
    return context


@transaction.atomic
def answer_question(
    *,
    conversation: Conversation,
    question: str,
    embedding_provider: EmbeddingProvider,
    generation_provider: GenerationProvider,
) -> Message:
    """The full ask-a-question flow: persist the user's message, run
    workspace-filtered retrieval scoped to the conversation's documents
    (if any), decide whether grounding is strong enough to answer at
    all, generate (or refuse), and persist the assistant message with
    its citations and usage record — all in one transaction so a
    mid-flight failure never leaves a half-written turn."""
    Message.objects.create(conversation=conversation, role=MessageRole.USER, content=question)

    query_embedding = embedding_provider.embed(text=question)
    ranked = retrieve_chunks(
        workspace_id=str(conversation.workspace_id),
        query_embedding=query_embedding,
        document_ids=conversation.document_scope or None,
    )
    # Grounding gate: chunks that matched but are too dissimilar to
    # trust are dropped before generation ever sees them — this is what
    # makes an off-topic question return "insufficient evidence" instead
    # of a generated answer stretched over weak context.
    grounded = [
        (chunk, distance)
        for chunk, distance in ranked
        if distance <= settings.RAG_MAX_GROUNDING_DISTANCE
    ]
    context = build_context(grounded)

    started = time.monotonic()
    try:
        result = generation_provider.generate(question=question, context=context)
    except ProviderUnavailableError as exc:
        raise ProviderUnavailableAPIError() from exc
    latency_ms = int((time.monotonic() - started) * 1000)

    assistant_message = Message.objects.create(
        conversation=conversation,
        role=MessageRole.ASSISTANT,
        content=result.answer,
        is_insufficient_evidence=not context,
    )

    citation_by_chunk = {str(c.id): c for c, _ in grounded}
    AnswerCitation.objects.bulk_create(
        [
            AnswerCitation(
                message=assistant_message,
                chunk=citation_by_chunk[citation.chunk_id],
                snippet=citation.snippet,
                order=order,
            )
            for order, citation in enumerate(result.citations)
            if citation.chunk_id in citation_by_chunk
        ]
    )

    ModelUsageRecord.objects.create(
        message=assistant_message,
        provider=type(generation_provider).__name__,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_ms=latency_ms,
    )

    conversation.save(update_fields=["updated_at"])
    return assistant_message
