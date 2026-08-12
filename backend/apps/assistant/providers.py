"""Embedding and generation provider abstractions (project rule: mock
external providers at module boundaries; unit tests must never call a
paid embedding/LLM provider). Only deterministic mock implementations
exist in this phase — no real Anthropic/OpenAI-style API key is
configured for this project yet (see docs/adr). Both interfaces are
designed so a real provider can be added later without the
retrieval/generation service layer changing."""

import hashlib
import re
from dataclasses import dataclass, field
from typing import Protocol

from django.conf import settings


class EmbeddingProvider(Protocol):
    def embed(self, *, text: str) -> list[float]: ...


class MockEmbeddingProvider:
    """Deterministic, dependency-free stand-in for a real embedding
    call: hashes the text into a fixed-length vector and L2-normalizes
    it. Same input always yields the same output (required for the
    deterministic mocked RAG test set and for idempotent re-indexing).
    Not semantically meaningful the way a real embedding model's output
    is — it clusters by shared vocabulary well enough for this
    portfolio's demo corpus and tests, nothing more."""

    def __init__(self, dimensions: int | None = None) -> None:
        self.dimensions = dimensions or settings.RAG_EMBEDDING_DIMENSIONS

    def embed(self, *, text: str) -> list[float]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        vector = [0.0] * self.dimensions
        if not tokens:
            vector[0] = 1.0
            return vector
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(self.dimensions):
                # Cycle through the digest's bytes to fill however many
                # dimensions are configured, regardless of digest length.
                byte = digest[i % len(digest)]
                vector[i] += (byte / 255.0) * 2 - 1  # map to [-1, 1]
        magnitude = sum(v * v for v in vector) ** 0.5
        if magnitude == 0:
            vector[0] = 1.0
            return vector
        return [v / magnitude for v in vector]


def get_embedding_provider() -> EmbeddingProvider:
    return MockEmbeddingProvider()


@dataclass(frozen=True)
class ContextChunk:
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    text: str
    distance: float


@dataclass(frozen=True)
class CitationResult:
    chunk_id: str
    snippet: str


@dataclass(frozen=True)
class GenerationResult:
    answer: str
    citations: list[CitationResult] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0


class GenerationProvider(Protocol):
    def generate(self, *, question: str, context: list[ContextChunk]) -> GenerationResult: ...


class ProviderUnavailableError(Exception):
    """Normalized failure for a provider call that could not complete
    (timeout, rate limit, outage) — retryable at the caller's
    discretion. Never raised by MockGenerationProvider itself (it has no
    network dependency to fail); exists so the service layer and its
    tests have one stable error type to handle regardless of which
    provider is configured."""


class MockGenerationProvider:
    """Deterministic answer construction — no network call, and no
    behavior a document's own text could ever influence beyond being
    quoted. This is the enforcement point for two of the phase's
    non-negotiable prompt-injection rules:

    - Retrieved chunk text is treated purely as data to quote from, never
      as instructions — nothing here parses or executes directives found
      in `context[*].text` (there's no eval/exec/tool-call path in this
      class at all, mock or not).
    - No tool execution of any kind — this method returns a plain string
      and a citation list; it has no ability to invoke anything else.

    Answers are illustrative, not fluent prose — a labeled portfolio
    demonstration of the retrieval-and-citation flow, not a claim about
    real generation quality (project rule against unsupported quality
    claims)."""

    def generate(self, *, question: str, context: list[ContextChunk]) -> GenerationResult:
        if not context:
            return GenerationResult(answer=_INSUFFICIENT_EVIDENCE_MESSAGE)

        citations = [CitationResult(chunk_id=c.chunk_id, snippet=_snippet(c.text)) for c in context]
        sources = ", ".join(f"{c.filename} (p.{c.page_number})" for c in context)
        answer = (
            f"Based on {len(context)} matching passage(s) — {sources} — here is what the "
            f"indexed documents say about \u201c{question.strip()}\u201d:\n\n"
            + "\n\n".join(f"- {_snippet(c.text, length=280)}" for c in context)
        )
        return GenerationResult(
            answer=answer,
            citations=citations,
            prompt_tokens=sum(len(c.text.split()) for c in context) + len(question.split()),
            completion_tokens=len(answer.split()),
        )


_INSUFFICIENT_EVIDENCE_MESSAGE = (
    "I don't have enough grounded information in the indexed documents to answer that. "
    "Try rephrasing the question or narrowing the document scope."
)


def _snippet(text: str, *, length: int = 200) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= length:
        return cleaned
    return cleaned[:length].rsplit(" ", 1)[0] + "\u2026"


def get_generation_provider() -> GenerationProvider:
    return MockGenerationProvider()
