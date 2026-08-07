# Architecture Overview

DocPilot AI — Intelligent Document & Workflow Automation. **Portfolio
demonstration project.** Metrics, integrations, and workflows described
anywhere in this repository are illustrative/sample unless stated
otherwise.

See [`docs/adr/0001-modular-monolith.md`](adr/0001-modular-monolith.md)
for the architectural decision this document assumes.

## System shape

A single Django/DRF **modular monolith** backend, a single React/TypeScript
frontend, and asynchronous background processing via Celery/Redis (not
yet implemented — lands in the async-processing phase). No microservices.

```
┌─────────────────────┐       ┌──────────────────────────────────┐
│   frontend/ (Vite,   │  HTTP │   backend/ (Django + DRF)         │
│   React, TypeScript) │──────▶│   config/  — settings, URL root   │
└─────────────────────┘       │   apps/    — one Django app per   │
                               │             bounded module        │
                               │   common/  — cross-cutting infra  │
                               │             (logging, middleware, │
                               │             error envelope)       │
                               └───────┬───────────────┬──────────┘
                                       │                │
                                 ┌─────▼─────┐   ┌───────▼──────┐
                                 │ PostgreSQL │   │    Redis      │
                                 │ (+pgvector)│   │ (cache, future │
                                 │            │   │  Celery broker)│
                                 └────────────┘   └───────────────┘
```

## Module boundaries

Each bounded piece of the product is its own Django app under
`backend/apps/`, not a separate service:

| App | Responsibility | Status |
|---|---|---|
| `apps.health` | Liveness/readiness probes | Implemented (Phase 0B) |
| `apps.accounts` | Custom user model, JWT auth (login/refresh/logout/session) | Implemented (Phase 2A backend, Phase 2B frontend) |
| `apps.workspaces` | Workspace isolation, membership, RBAC | Implemented (Phase 2A backend; frontend selector/nav gating in Phase 2B — membership-management UI itself still backend-only) |
| `apps.audit` | Immutable audit-event log | Implemented (Phase 2A) |
| `apps.documents` | Upload, storage, parsing/OCR orchestration | Planned (Phase 3–4) |
| `apps.extraction` | Structured extraction, confidence, validation, review | Planned (Phase 5) |
| `apps.assistant` | Semantic indexing, RAG Q&A with citations | Planned (Phase 6) |
| `apps.workflows` | Approval/automation workflow engine + builder | Planned (Phase 7) |
| `apps.integrations` | Webhooks, notifications, audit trail | Planned (Phase 8) |
| `apps.analytics` | Operational analytics | Planned (Phase 9) |

Cross-cutting infrastructure — correlation-ID middleware, structured
logging, the stable API error envelope — lives in `backend/common/` and is
shared by every app. It never contains business logic (see the
non-negotiable rule keeping business logic out of views/serializers/tasks
— business rules belong in each app's own service/selector layer).

## Why a modular monolith, not microservices

See [ADR-0001](adr/0001-modular-monolith.md) for the full reasoning.
Short version: at this project's actual scale (a single team, a bounded
demo domain, no independent-scaling requirement that's been demonstrated),
microservices would add deployment/operational complexity — network
boundaries, distributed transactions, service discovery — without a
matching benefit. Module boundaries are enforced by Django app boundaries
and code review instead, which is enough to keep the system navigable and
still leaves a real path to extraction later if a specific module ever
needs independent scaling.

## Request flow

1. Frontend calls the DRF API (`/api/...`).
2. `common.middleware.CorrelationIdMiddleware` attaches a correlation ID
   (reused from an inbound `X-Correlation-ID` header, or generated) to the
   request, echoed back on the response, and available to every log line
   emitted while handling the request.
3. The view delegates to a focused service/selector function for anything
   beyond request/response shaping (views stay thin).
4. Errors — validation, permission, not-found, or truly unexpected — all
   flow through `common.exceptions.stable_exception_handler`, which
   normalizes every error response to `{"error": {"code", "message",
   "details"}}` and ensures unhandled exceptions never leak internal
   detail to the client (logged server-side instead, with the correlation
   ID attached).

## Background processing

Not implemented yet (Phase 0D scope is infrastructure only). The plan,
per the async-processing phase: Celery workers consume from Redis for
OCR, extraction, embedding, and notification/webhook delivery — anything
that shouldn't block an HTTP request. Tasks must be idempotent (retrying
a task that partially completed must not double-process a document or
double-send a notification) and must only retry genuinely retryable
failures (a validation failure is not retried indefinitely).

## Environments & configuration

Environment-based Django settings (`backend/config/settings/`):
`base` (shared, nothing environment-specific hardcoded) → `local` /
`test` / `production`. All environment-varying values (secrets, hosts,
database/broker URLs) come from environment variables via
`django-environ`, never hardcoded. See
[`backend/README.md`](../backend/README.md) for the full settings-module
breakdown, and [`docs/adr`](adr/) for why particular choices were made.

Time is handled in UTC internally throughout the backend
(`USE_TZ = True`, `TIME_ZONE = "UTC"`); conversion to a user's local time
zone is a presentation-layer concern only.

## Health & readiness

- `GET /api/health/` — liveness only, always 200 if the process can serve
  requests.
- `GET /api/readiness/` — checks PostgreSQL and Redis connectivity, 503 if
  either is unreachable. The response never includes the raw
  connection-error text — see `backend/apps/health/services.py`.

## Local infrastructure

`docker-compose.yml` (repo root) runs PostgreSQL (`pgvector/pgvector`
image, ready for vector columns once a later phase needs them) and Redis,
each with a healthcheck and a named persistent volume, plus the backend
service itself. The frontend is not containerized — `npm run dev` already
covers local iteration reliably. MinIO (S3-compatible storage) is
deferred to the document-storage phase that will actually configure and
use it.

## Observability

- Structured (JSON) logs, one object per line, tagged with the request's
  correlation ID — see `backend/common/logging.py`.
- Sentry wired but inert unless `SENTRY_DSN` is set
  (`backend/config/settings/production.py`).
- Never logged: secrets, tokens, passwords, full document contents,
  extracted field values.

## What this document intentionally does not cover yet

Authentication (sign-in, session bootstrap, protected routes, logout)
and workspace selection/permission-aware navigation are implemented
end-to-end (Phase 2A backend + Phase 2B frontend). Workspace membership
*management* (invite/remove/change-role/transfer-ownership) has a
backend API (Phase 2A) but no frontend UI yet. The extraction pipeline,
document upload, the RAG assistant, the workflow engine, and analytics
are all designed in their respective phase prompts but not implemented
— this document describes verified, implemented reality plus the module
map those phases will fill in, not a forward-looking design spec for
all of them.
