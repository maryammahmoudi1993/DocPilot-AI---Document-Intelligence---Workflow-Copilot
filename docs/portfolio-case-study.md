# Portfolio Case Study: DocPilot AI

## What it is

A document-intelligence and workflow-automation product, built end to
end as a portfolio demonstration: upload a document, have it
processed and structured automatically, review and correct what the
pipeline got wrong, approve it, ask questions about it in natural
language with citations back to the source, and let an automation
workflow notify/webhook the result — with every step producing an
immutable audit trail and feeding real operational analytics.

**Portfolio demonstration project.** Every metric, integration, and
workflow in the running application is sample data, illustrative, or
simulated unless labeled otherwise — see
[`docs/limitations.md`](limitations.md) for the honest boundary between
what's real and what's a labeled stand-in.

## The engineering problem this demonstrates

Most "AI document processing" demos are a single happy-path script: pick
a file, call an LLM, print JSON. The actual engineering problem — the
one real teams pay for — is everything around that call:

- **Async, resumable processing** that survives a worker crash mid-job
  without double-processing a document or double-charging a provider.
- **Confidence-aware human review** — knowing which extracted fields to
  trust and which to route to a person, and letting that person correct
  the record without losing the audit trail of what changed and why.
- **Real authorization**, not a decorative role dropdown — every
  workspace-scoped request re-derives the caller's actual permission
  from the database on every call, not from a client-supplied claim.
- **Grounded answers, not hallucinated ones** — a RAG assistant that
  cites the specific chunk of the specific document it's answering from,
  so a wrong answer is checkable, not just plausible-sounding.
- **Operational trustworthiness** — signed, idempotent webhooks;
  encrypted-at-rest integration secrets; an audit log nothing can edit
  through the public API; structured logs that redact secrets by
  default even when a caller forgets to.

DocPilot AI implements all of the above for real, against a real
(if intentionally mock-provider-backed for the paid-API-dependent
pieces) pipeline — not stubbed out, not faked for the demo.

## Architecture decisions worth calling out

- **Modular monolith, not microservices** (see
  [ADR-0001](adr/0001-modular-monolith.md)) — the honest call for this
  project's actual scale, made explicit rather than defaulted to
  either extreme.
- **Provider abstraction at every AI/OCR boundary** — OCR, document
  classification, and RAG embedding/generation are all behind a
  `Protocol` interface with a deterministic mock as the default and a
  real implementation (Tesseract for OCR) swappable in without touching
  a single caller. This is what actually lets the project keep its own
  rule — unit tests never call a paid provider — without sacrificing a
  real, demonstrable pipeline.
- **Idempotency as a first-class constraint**, not an afterthought:
  processing jobs, webhook deliveries, and approval decisions are all
  designed so a retry, a duplicate request, or a re-run of a seed
  command is safe by construction, not by convention.
- **A security posture that's honest about its own limits.** The default
  malware scanner (`apps/documents/scanning.py`) explicitly documents
  that it only catches the industry-standard EICAR test file, not real
  malware — a documented extension point, not an overclaimed feature.
  See [`docs/security-assumptions.md`](security-assumptions.md).

## Scope, honestly

- No real LLM/embedding API key is wired in anywhere — a deliberate
  scope decision (see [`docs/limitations.md`](limitations.md)), not a
  missing feature. The RAG assistant's grounding/citation mechanics are
  real; the model behind them is a deterministic mock.
- Extraction confidence scores are illustrative, labeled as such in the
  UI, not a calibrated accuracy metric from a ground-truth evaluation.
- No production deployment has received real traffic — "deployment
  validated" means the production Docker images build, boot, and pass
  health checks locally.

## Try it

See [`docs/demo-script.md`](demo-script.md) for a guided 60–90 second
walkthrough, or the root [`README.md`](../README.md) for the full setup
instructions to run it yourself.
