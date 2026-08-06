# ADR-0001: Modular monolith, not microservices

Status: Accepted
Date: 2026-08-06

## Context

DocPilot AI is a portfolio demonstration of document intelligence and
workflow automation: upload → OCR/parsing → structured extraction →
human review → approval → semantic indexing → RAG Q&A → approval
workflow → webhook/notification → audit → analytics. It's built and
operated by a single developer, has a bounded (if broad) feature set, and
has no demonstrated requirement to scale any one piece of that pipeline
independently of the others.

The project's required technology direction explicitly calls for "a
modular monolith with asynchronous background processing" and says not to
introduce microservices — this ADR records *why* that's the right call
here, not just that it's mandated.

## Decision

Build one Django/DRF backend process (deployed as one unit, though
horizontally scalable behind a load balancer) with internal module
boundaries enforced by Django app structure
(`backend/apps/<module>/`) and code review, not by network boundaries.
Background/async work (OCR, extraction, embedding, notification delivery)
runs via Celery workers reading from a shared Redis broker — a separate
*process*, not a separate *service* with its own API, data ownership, and
deployment lifecycle.

## Consequences

**Easier:**
- One codebase, one dependency set, one deployment artifact, one test
  suite to reason about end-to-end.
- Cross-module operations (e.g. "approve this document, which triggers a
  workflow, which sends a webhook, which writes an audit event") stay
  simple function calls / Django transactions instead of distributed
  transactions or sagas across service boundaries.
- Local development stays simple: one `docker compose up` for
  infrastructure, one backend process to run, not N services to
  orchestrate.
- Refactoring a module boundary is a code change, not a coordinated
  multi-service migration.

**Harder / foreclosed (accepted trade-offs):**
- Every module shares one deployment cadence — you can't deploy the
  extraction pipeline without also being able to deploy everything else
  in the same release.
- Every module shares one process's resource profile — a CPU-heavy OCR
  task and a latency-sensitive API request compete for the same backend
  process's resources unless pushed to a Celery worker (which they are,
  once implemented).
- If a specific module ever needed genuinely independent scaling (e.g.
  OCR processing at a volume no single deployment could absorb), it would
  need to be extracted later. That's a real cost, judged smaller than the
  cost of building distributed-systems complexity for a scale this
  project has never demonstrated it needs.

## Alternatives considered

**Microservices per module** (documents, extraction, assistant,
workflows, integrations as separate deployable services): rejected.
Would add network boundaries, service discovery, distributed
transactions/eventual consistency, and per-service CI/CD/observability
stacks — real engineering cost — for a single-developer portfolio project
with no independent-scaling requirement to justify it. The "impressive
architecture" case for microservices doesn't hold up against "boring,
reliable, and actually finished."

**Fully synchronous monolith (no background workers)**: rejected. OCR,
embedding generation, and webhook delivery are all slow/unreliable enough
(and explicitly required to be retried, not retried indefinitely on
validation failures) that blocking an HTTP request on them would make the
API unusable. Celery + Redis gets async processing without the
distributed-systems cost of full microservices.
