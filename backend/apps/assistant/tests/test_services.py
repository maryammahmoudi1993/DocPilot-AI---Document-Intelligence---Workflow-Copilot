"""Service-layer tests for chunking, indexing, retrieval, and grounded
answer generation. Uses the deterministic mock providers throughout —
the project's "deterministic mocked RAG test set"."""

import pytest

from apps.assistant import services
from apps.assistant.exceptions import ProviderUnavailableAPIError
from apps.assistant.models import (
    DocumentChunk,
    Message,
    MessageRole,
    ModelUsageRecord,
)
from apps.assistant.providers import (
    MockEmbeddingProvider,
    MockGenerationProvider,
    ProviderUnavailableError,
)
from apps.assistant.services import InvalidDocumentScopeError
from tests.factories import (
    ConversationFactory,
    DocumentChunkFactory,
    DocumentFactory,
    UserFactory,
    WorkspaceFactory,
)


@pytest.mark.django_db
class TestChunkPages:
    def test_chunks_do_not_span_page_boundaries(self):
        pages = [(1, "word " * 300), (2, "other " * 300)]

        spans = services.chunk_pages(pages, chunk_size=100)

        assert all(span.page_number in (1, 2) for span in spans)
        page_1_text = " ".join(s.text for s in spans if s.page_number == 1)
        assert "other" not in page_1_text

    def test_is_deterministic(self):
        pages = [(1, "some invoice text here")]

        first = services.chunk_pages(pages, chunk_size=10)
        second = services.chunk_pages(pages, chunk_size=10)

        assert first == second


@pytest.mark.django_db
class TestIndexDocument:
    # DocumentChunk.embedding is a fixed-width pgvector column (see
    # settings.RAG_EMBEDDING_DIMENSIONS) — tests that persist chunks
    # must use a provider producing that exact width.

    def test_creates_one_chunk_per_span_with_embeddings(self):
        document = DocumentFactory()
        provider = MockEmbeddingProvider(dimensions=256)

        chunks = services.index_document(
            document, page_texts=[(1, "Vendor: Acme"), (2, "Total: 100.00")], provider=provider
        )

        assert len(chunks) == 2
        assert all(len(c.embedding) == 256 for c in chunks)
        assert {c.page_number for c in chunks} == {1, 2}

    def test_is_idempotent_reindexing_replaces_old_chunks(self):
        document = DocumentFactory()
        provider = MockEmbeddingProvider(dimensions=256)
        services.index_document(document, page_texts=[(1, "first version")], provider=provider)

        services.index_document(document, page_texts=[(1, "second version")], provider=provider)

        chunks = DocumentChunk.objects.filter(document=document)
        assert chunks.count() == 1
        assert chunks.first().text == "second version"

    def test_empty_document_produces_no_chunks(self):
        document = DocumentFactory()

        chunks = services.index_document(
            document, page_texts=[], provider=MockEmbeddingProvider(dimensions=256)
        )

        assert chunks == []


@pytest.mark.django_db
class TestRetrieveChunks:
    def test_returns_only_same_workspace_chunks(self):
        workspace_a = WorkspaceFactory()
        workspace_b = WorkspaceFactory()
        doc_a = DocumentFactory(workspace=workspace_a)
        doc_b = DocumentFactory(workspace=workspace_b)
        DocumentChunkFactory(
            document=doc_a, workspace=workspace_a, embedding=[1.0, 0.0] + [0.0] * 254
        )
        DocumentChunkFactory(
            document=doc_b, workspace=workspace_b, embedding=[1.0, 0.0] + [0.0] * 254
        )

        results = services.retrieve_chunks(
            workspace_id=str(workspace_a.id), query_embedding=[1.0, 0.0] + [0.0] * 254
        )

        assert len(results) == 1
        assert results[0][0].document_id == doc_a.id

    def test_document_scope_filters_to_the_requested_documents(self):
        workspace = WorkspaceFactory()
        doc_in_scope = DocumentFactory(workspace=workspace)
        doc_out_of_scope = DocumentFactory(workspace=workspace)
        DocumentChunkFactory(
            document=doc_in_scope, workspace=workspace, embedding=[1.0, 0.0] + [0.0] * 254
        )
        DocumentChunkFactory(
            document=doc_out_of_scope, workspace=workspace, embedding=[1.0, 0.0] + [0.0] * 254
        )

        results = services.retrieve_chunks(
            workspace_id=str(workspace.id),
            query_embedding=[1.0, 0.0] + [0.0] * 254,
            document_ids=[str(doc_in_scope.id)],
        )

        assert {r[0].document_id for r in results} == {doc_in_scope.id}

    def test_a_document_scope_from_another_workspace_cannot_leak_chunks(self):
        workspace = WorkspaceFactory()
        other_workspace = WorkspaceFactory()
        other_doc = DocumentFactory(workspace=other_workspace)
        DocumentChunkFactory(
            document=other_doc, workspace=other_workspace, embedding=[1.0, 0.0] + [0.0] * 254
        )

        results = services.retrieve_chunks(
            workspace_id=str(workspace.id),
            query_embedding=[1.0, 0.0] + [0.0] * 254,
            document_ids=[str(other_doc.id)],
        )

        assert results == []

    def test_orders_by_similarity_best_first(self):
        workspace = WorkspaceFactory()
        document = DocumentFactory(workspace=workspace)
        close = DocumentChunkFactory(
            document=document,
            workspace=workspace,
            chunk_index=0,
            embedding=[0.9, 0.1] + [0.0] * 254,
        )
        far = DocumentChunkFactory(
            document=document,
            workspace=workspace,
            chunk_index=1,
            embedding=[0.0, 1.0] + [0.0] * 254,
        )

        results = services.retrieve_chunks(
            workspace_id=str(workspace.id), query_embedding=[1.0, 0.0] + [0.0] * 254
        )

        ids = [r[0].id for r in results]
        assert ids.index(close.id) < ids.index(far.id)


@pytest.mark.django_db
class TestBuildContext:
    def test_stays_within_the_character_budget(self):
        workspace = WorkspaceFactory()
        document = DocumentFactory(workspace=workspace)
        chunks = [
            (DocumentChunkFactory(document=document, workspace=workspace, text="x" * 400), 0.1),
            (DocumentChunkFactory(document=document, workspace=workspace, text="y" * 400), 0.2),
            (DocumentChunkFactory(document=document, workspace=workspace, text="z" * 400), 0.3),
        ]

        context = services.build_context(chunks, budget_chars=900)

        assert len(context) == 2

    def test_always_includes_at_least_one_chunk_even_if_it_exceeds_the_budget(self):
        workspace = WorkspaceFactory()
        document = DocumentFactory(workspace=workspace)
        chunks = [
            (DocumentChunkFactory(document=document, workspace=workspace, text="x" * 5000), 0.1)
        ]

        context = services.build_context(chunks, budget_chars=100)

        assert len(context) == 1


@pytest.mark.django_db
class TestCreateConversation:
    def test_rejects_a_document_scope_with_an_unknown_id(self):
        workspace = WorkspaceFactory()
        user = UserFactory()

        with pytest.raises(InvalidDocumentScopeError):
            services.create_conversation(
                workspace=workspace,
                user=user,
                document_scope=["00000000-0000-0000-0000-000000000000"],
            )

    def test_accepts_a_scope_of_real_documents_in_the_workspace(self):
        workspace = WorkspaceFactory()
        document = DocumentFactory(workspace=workspace)
        user = UserFactory()

        conversation = services.create_conversation(
            workspace=workspace, user=user, document_scope=[str(document.id)]
        )

        assert conversation.document_scope == [str(document.id)]


@pytest.mark.django_db
class TestAnswerQuestion:
    def _grounded_setup(self):
        workspace = WorkspaceFactory()
        document = DocumentFactory(workspace=workspace, filename="invoice.pdf")
        embedding_provider = MockEmbeddingProvider(dimensions=256)
        services.index_document(
            document,
            page_texts=[(1, "The total due is five hundred dollars.")],
            provider=embedding_provider,
        )
        conversation = ConversationFactory(workspace=workspace)
        return conversation, embedding_provider

    def test_a_grounded_question_returns_an_answer_with_citations(self):
        conversation, embedding_provider = self._grounded_setup()

        message = services.answer_question(
            conversation=conversation,
            question="What is the total due?",
            embedding_provider=embedding_provider,
            generation_provider=MockGenerationProvider(),
        )

        assert message.role == MessageRole.ASSISTANT
        assert message.is_insufficient_evidence is False
        assert message.citations.count() >= 1

    def test_citation_page_matches_the_source_chunk(self):
        conversation, embedding_provider = self._grounded_setup()

        message = services.answer_question(
            conversation=conversation,
            question="What is the total due?",
            embedding_provider=embedding_provider,
            generation_provider=MockGenerationProvider(),
        )

        citation = message.citations.first()
        assert citation.chunk.page_number == 1

    def test_an_unsupported_question_returns_insufficient_evidence(self):
        workspace = WorkspaceFactory()
        conversation = ConversationFactory(workspace=workspace)
        # No documents indexed at all in this workspace.

        message = services.answer_question(
            conversation=conversation,
            question="What is the meaning of life?",
            embedding_provider=MockEmbeddingProvider(dimensions=256),
            generation_provider=MockGenerationProvider(),
        )

        assert message.is_insufficient_evidence is True
        assert message.citations.count() == 0

    def test_a_weakly_matched_question_is_also_treated_as_insufficient_evidence(self, settings):
        conversation, embedding_provider = self._grounded_setup()
        # Force the grounding gate closed regardless of retrieval score.
        settings.RAG_MAX_GROUNDING_DISTANCE = -1.0

        message = services.answer_question(
            conversation=conversation,
            question="Completely unrelated question about astrophysics.",
            embedding_provider=embedding_provider,
            generation_provider=MockGenerationProvider(),
        )

        assert message.is_insufficient_evidence is True

    def test_document_scope_limits_retrieval_to_selected_documents(self):
        workspace = WorkspaceFactory()
        in_scope_doc = DocumentFactory(workspace=workspace, filename="in-scope.pdf")
        out_of_scope_doc = DocumentFactory(workspace=workspace, filename="out-of-scope.pdf")
        embedding_provider = MockEmbeddingProvider(dimensions=256)
        services.index_document(
            in_scope_doc, page_texts=[(1, "Alpha document content.")], provider=embedding_provider
        )
        services.index_document(
            out_of_scope_doc,
            page_texts=[(1, "Alpha document content.")],
            provider=embedding_provider,
        )
        conversation = ConversationFactory(
            workspace=workspace, document_scope=[str(in_scope_doc.id)]
        )

        message = services.answer_question(
            conversation=conversation,
            question="Tell me about the alpha document.",
            embedding_provider=embedding_provider,
            generation_provider=MockGenerationProvider(),
        )

        cited_docs = {c.chunk.document_id for c in message.citations.all()}
        assert cited_docs <= {in_scope_doc.id}

    def test_provider_failure_is_normalized_to_a_stable_error(self):
        conversation, embedding_provider = self._grounded_setup()

        class BoomProvider:
            def generate(self, *, question, context):
                raise ProviderUnavailableError("timeout")

        with pytest.raises(ProviderUnavailableAPIError):
            services.answer_question(
                conversation=conversation,
                question="What is the total due?",
                embedding_provider=embedding_provider,
                generation_provider=BoomProvider(),
            )

    def test_model_usage_record_never_stores_prompt_or_answer_text(self):
        conversation, embedding_provider = self._grounded_setup()

        message = services.answer_question(
            conversation=conversation,
            question="What is the total due?",
            embedding_provider=embedding_provider,
            generation_provider=MockGenerationProvider(),
        )

        usage = message.usage
        usage_fields = {f.name for f in ModelUsageRecord._meta.get_fields()}
        assert "content" not in usage_fields
        assert "prompt" not in usage_fields
        assert usage.prompt_tokens > 0

    def test_persists_the_user_message_too(self):
        conversation, embedding_provider = self._grounded_setup()

        services.answer_question(
            conversation=conversation,
            question="What is the total due?",
            embedding_provider=embedding_provider,
            generation_provider=MockGenerationProvider(),
        )

        assert Message.objects.filter(
            conversation=conversation, role=MessageRole.USER, content="What is the total due?"
        ).exists()
