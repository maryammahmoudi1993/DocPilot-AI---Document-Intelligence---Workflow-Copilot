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

## Logging

Structured (one JSON object per line), tagged with a per-request
correlation ID (`X-Correlation-ID` request/response header — see
`common/middleware.py` and `common/logging.py`). Never log secrets, tokens,
passwords, full document contents, or extracted field values.

## Known environment limitation (dev sandbox used to build this phase)

In the sandbox this phase was developed in, `manage.py makemigrations
--check` hung rather than failing fast when `DATABASE_URL` pointed at an
unreachable PostgreSQL host — the network silently dropped the connection
instead of refusing it (Docker Desktop's engine was also unreachable from
that same sandboxed shell, so a container-backed Postgres wasn't an
option either). The validation commands that need a real Postgres
connection were run with a temporary SQLite `DATABASE_URL` override
instead, since this phase has no models to make the backend choice
matter. This is not a code issue — a real Postgres instance (local,
Dockerized, or a CI service container) behaves normally. Don't reach for
the same SQLite-override workaround once real Postgres-dependent models
exist; fix or route around the actual connectivity problem instead.
