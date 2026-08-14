# DocPilot AI — Backend

Django + Django REST Framework modular monolith. No microservices. See the
repository root `CLAUDE.md` (local-only) and `docs/` (local-only, gitignored)
for broader project context.

## Requirements

- Python 3.12 (pinned in `pyproject.toml`'s `requires-python`)
- PostgreSQL 16+ (with the `pgvector` extension available — not required
  until a later phase introduces vector-backed models)
- Redis 7+

Local Postgres/Redis servers are not bundled yet — that lands in the
infrastructure phase (`docker-compose.yml`). Until then, point
`DATABASE_URL` / `REDIS_URL` at whatever local or containerized instances
you run yourself.

## Setup

```bash
cd backend
python3.12 -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env   # then fill in real values
```

## Common commands

```bash
python manage.py check                          # Django system checks
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py runserver
python manage.py spectacular --file schema.yaml  # OpenAPI schema

ruff check .
ruff format .
mypy .
pytest                                           # unit tests (SQLite, no DB server needed)
pytest --cov                                     # with coverage report
```

## Settings modules

- `config.settings.base` — shared settings; nothing environment-specific is
  hardcoded, everything varying by environment is read via `django-environ`.
- `config.settings.local` — default for `manage.py` locally. Reads
  `backend/.env`. Falls back to an insecure `SECRET_KEY` only for
  convenience if `DJANGO_SECRET_KEY` isn't set.
- `config.settings.test` — used by `pytest` (configured in `pyproject.toml`).
  Uses an in-memory SQLite database instead of PostgreSQL — documented
  deviation: no model in this phase depends on Postgres/pgvector-specific
  behavior. Revisit once one does.
- `config.settings.production` — used by `config.wsgi`/`config.asgi`. Fails
  fast (`ImproperlyConfigured`) if `DJANGO_SECRET_KEY` or
  `DJANGO_ALLOWED_HOSTS` are missing; enables HTTPS/HSTS security settings;
  initializes Sentry if `SENTRY_DSN` is set.

## Health & readiness

- `GET /api/health/` — liveness only (process is up). Always 200 if the
  process can serve requests at all.
- `GET /api/readiness/` — checks database and Redis connectivity, returns
  503 if either is unreachable. Response never includes the raw
  connection-error text (see `common/exceptions.py` and
  `apps/health/services.py` — internal errors are logged server-side with
  the request's correlation ID, never returned to the client).

## API errors

Every DRF-routed error response uses one stable envelope:

```json
{"error": {"code": "not_found", "message": "...", "details": null}}
```

`code` is a stable, machine-readable identifier — see
`common/exceptions.py` for the full mapping. Unhandled exceptions become
`{"error": {"code": "internal_error", ...}}` with a generic message; the
real exception is logged, never returned to the client.

## Authentication, workspaces, and RBAC

**Login is by email**, not a separate username (`apps.accounts.User`,
`USERNAME_FIELD = "email"` — see `docs/adr/0002-custom-user-model.md`).

Auth is JWT (`djangorestframework-simplejwt`):

| Endpoint | Behavior |
|---|---|
| `POST /api/auth/login/` | `{email, password}` → `{access, user}`; sets the refresh token as an **httpOnly** cookie (never readable by frontend JS — see the project rule against long-lived secrets in insecure browser storage). Throttled (`10/min`). |
| `POST /api/auth/refresh/` | Reads the refresh cookie (never the request body), rotates it (old one is blacklisted immediately — `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION`), returns a new `access`. Throttled (`30/min`). |
| `POST /api/auth/logout/` | Blacklists the current refresh token, clears the cookie. |
| `GET /api/auth/session/` | Current user + every workspace they belong to (with their role in each) + their active-workspace pointer. Frontend session-bootstrap endpoint. |
| `PATCH /api/auth/active-workspace/` | Sets which workspace the frontend should preselect. **Not an authorization mechanism** — see below. |

Access tokens are short-lived (15 min) and meant for the `Authorization:
Bearer <token>` header, kept in memory by the frontend — never
`localStorage` (XSS-exfiltrable). Refresh tokens (7 days) live only in
the httpOnly cookie.

### Workspaces and roles

`apps.workspaces.Workspace` + `WorkspaceMembership` (one row per
user-per-workspace, with a `role`). Five roles: **Owner**, **Admin**,
**Finance Manager**, **Reviewer**, **Viewer**. Only Owner/Admin can
manage membership (`apps.workspaces.models.MEMBERSHIP_MANAGER_ROLES`);
every member can read the member list. Ownership changes hands only via
`POST /api/workspaces/<id>/transfer-ownership/` (owner-only,
transactional — the old owner becomes Admin, never left roleless) —
`PATCH .../members/<id>/` explicitly refuses to set `role: owner`
directly.

**Every workspace-scoped endpoint re-derives the caller's role from a
real `WorkspaceMembership` row on every single request** (see
`apps/workspaces/permissions.py` and `apps/workspaces/selectors.py`) —
never from a client-supplied header, cookie, or the user's
`active_workspace` convenience pointer. That pointer exists purely so
the frontend knows which workspace to preselect on load; forging it
changes nothing about what a request is actually authorized to touch
(and `set_active_workspace` itself rejects setting it to a workspace the
caller isn't a member of, in `apps/workspaces/services.py`).

### Demo data

```bash
python manage.py seed_demo_data       # workspace + 5 role users
python manage.py seed_demo_documents  # + the synthetic sample invoice/contract
python manage.py reset_demo_data      # clears + rebuilds the demo workspace's data
```

All three are idempotent. `seed_demo_data` creates `Demo Workspace` and
one user per role (`owner@demo.docpilot.ai`, `admin@…`, `finance@…`,
`reviewer@…`, `viewer@…`), all with the same password the command
prints to stdout — a portfolio-demo credential, not a real secret, safe
to have in this README. `seed_demo_documents` (requires
`seed_demo_data` to have run first) uploads the two entirely-synthetic
sample documents in `apps/documents/fixtures/` through the real upload
path — see that directory's own README for provenance.

## Documents and storage

`apps.documents` manages workspace-scoped file uploads on top of an
S3-compatible object store (MinIO locally, real S3 in deployment — see
`docs/adr/0004-storage-abstraction.md`). Files are never public; the
only way to read one back is a short-lived signed URL.

| Endpoint | Behavior |
|---|---|
| `GET /api/workspaces/<id>/documents/` | List, filtered (`status`, `content_type`), searched (`search`, by filename), sorted (`ordering`), paginated (`page`, `page_size`). |
| `POST /api/workspaces/<id>/documents/` | Upload (`multipart/form-data`, field `file`). Validates extension, size, declared MIME type, and file-content signature (magic bytes) before storing; rejects duplicates by SHA-256 within the workspace. |
| `GET /api/workspaces/<id>/documents/<doc_id>/` | Detail, including a freshly-generated signed `download_url`. |
| `DELETE /api/workspaces/<id>/documents/<doc_id>/` | Deletes the DB row and the underlying storage object (storage delete only happens after the DB transaction commits). |
| `POST /api/workspaces/<id>/documents/<doc_id>/archive/` | Marks a document archived (soft, reversible in the data model; not currently exposed as an "unarchive" endpoint). |
| `POST /api/workspaces/<id>/documents/bulk-archive/` | `{document_ids: [...]}` — all-or-nothing: rejects the whole request if any id doesn't resolve to a document in this workspace, before archiving any of them. |
| `POST /api/workspaces/<id>/documents/bulk-delete/` | Same all-or-nothing validation, for delete. |

All document endpoints require workspace membership
(`apps.workspaces.permissions.IsWorkspaceMember`) and are scoped by
`workspace_id` in the URL — a document ID from another workspace 404s
rather than leaking existence (IDOR protection). Every
create/archive/delete is recorded as an audit event
(`apps.audit`).

Supported file types: PDF, PNG, JPEG, DOCX, XLSX, CSV, TXT
(`apps/documents/validation.py`). Max upload size and signed-URL expiry
are configurable via `DOCUMENT_MAX_UPLOAD_SIZE_BYTES` and
`DOCUMENT_SIGNED_URL_EXPIRY_SECONDS`.

Running locally via `docker compose up` starts a MinIO container and a
one-shot `minio-init` service that creates the bucket
(`DOCUMENT_STORAGE_BUCKET`) on startup. Running the backend natively
instead requires a MinIO (or real S3) instance reachable at
`DOCUMENT_STORAGE_ENDPOINT_URL` — see `backend/.env.example`.

## Logging

Structured (one JSON object per line), tagged with a per-request
correlation ID (`X-Correlation-ID` request/response header — see
`common/middleware.py` and `common/logging.py`). Never log secrets, tokens,
passwords, full document contents, or extracted field values.

## Modules beyond auth/documents

Everything below has its own API surface, service/selector layer, and
test suite under `apps/<name>/`. See
[`docs/architecture-overview.md`](../docs/architecture-overview.md) for
the full module map and how these fit together, and each app's own
`views.py`/`urls.py` (or `/api/schema/docs/` at runtime) for the
authoritative endpoint list — this README intentionally doesn't
duplicate the OpenAPI schema by hand.

| App | What it adds |
|---|---|
| `apps.processing` | Celery pipeline: digital-text extraction (pypdf), per-page OCR routing, deterministic keyword classification. `ProcessingJob` state machine with normalized retryable-vs-non-retryable errors and exponential backoff. |
| `apps.extraction` | Structured field extraction, confidence scoring, validation issues, human correction (`FieldCorrection`), workspace-scoped review queue. |
| `apps.assistant` | Document chunking + embedding (pgvector), conversation/message history, grounded RAG answers with citations back to source chunks. Mock embedding/LLM provider only — no real API key configured (see `docs/limitations.md`). |
| `apps.workflows` | Versioned visual workflow definitions (nodes/edges), execution runs, and the `request_approval`/`send_notification`/`trigger_webhook` action nodes that call into `apps.approvals`/`apps.notifications`. |
| `apps.approvals` | `ApprovalRequest` lifecycle — assignment, comments, expiration, idempotent role-based `decide()` (repeating a decision is a safe no-op; a conflicting decision is rejected). |
| `apps.notifications` | In-app notifications, `WebhookEndpoint` (Fernet-encrypted secrets, never returned by the API), HMAC-SHA256-signed idempotent `WebhookDelivery` via a retrying Celery task, log-only email adapter. |
| `apps.audit` | Read-only, immutable audit-event log — no update/delete endpoint exists anywhere in this app. |
| `apps.analytics` | No models of its own — workspace-scoped aggregation queries over the apps above (dashboard summary, processing trends, review rate, workflow success rate, average approval duration). |

## Malware scanning

`apps/documents/scanning.py` — a `MalwareScanProvider` interface wired
into `apps.documents.services.create_document`, ahead of the storage
write. The default provider (`DOCUMENT_MALWARE_SCAN_PROVIDER=eicar`)
checks for the industry-standard EICAR antivirus test signature — no
paid service, safe in unit tests — and is not a general malware scanner;
see [`docs/security-assumptions.md`](../docs/security-assumptions.md)
for what it does and doesn't claim to catch, and the interface itself
for how a real AV engine would be wired in behind it.

## Production

`Dockerfile.prod` builds the gunicorn-served production image (also used
for the Celery worker, with a different container command); see
[`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md) for the full release
process, required environment variables, and rollback procedure.
`config.settings.production` fails fast if `DJANGO_SECRET_KEY`,
`DJANGO_ALLOWED_HOSTS`, or `INTEGRATION_SECRET_KEY` are unset.
