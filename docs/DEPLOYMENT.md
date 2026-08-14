# Deployment

The production release process: images, required configuration, the
release/migration step, and rollback. Referenced from
`docker-compose.prod.yml`, `backend/Dockerfile.prod`, and
`backend/pyproject.toml`'s production extras.

## Why no specific cloud provider is targeted

This is a portfolio project, not a company with a chosen cloud vendor.
Rather than couple the deployment story to one provider's proprietary
tooling (which would make the release process a demonstration of that
vendor's console, not of this project's engineering), the deployable
unit is three plain Docker images plus a production-parity Compose file
(`docker-compose.prod.yml`) that any container platform — a VM running
Docker, a managed container service, a PaaS with a Dockerfile deploy
path — can run with the same required environment variables. The
Compose file itself is meant as a **local validation and reference
manifest**, not a claim that `docker compose up` on a laptop constitutes
a production deployment.

## Images

| Image | Built from | Notes |
|---|---|---|
| Backend (web) | `backend/Dockerfile.prod` | gunicorn, non-root user, same system packages (`tesseract-ocr`, `poppler-utils`, `libpq5`) as the dev image (`backend/Dockerfile`). |
| Backend (worker) | `backend/Dockerfile.prod` (same image, `celery -A config worker` command) | See the `celery-worker` service in `docker-compose.prod.yml`. |
| Frontend | `frontend/Dockerfile` | Multi-stage: Vite build in a `node` image → served from `nginx`, which never contains `node_modules`, source TypeScript, or a Node runtime. `nginx.conf` adds SPA fallback (client-side routes must not 404 on a hard refresh) and long-cache headers for content-hashed assets vs. never-cache on `index.html`. |

Neither image runs `manage.py runserver` — Django's own documentation
states it is not fit for production; gunicorn serves the backend
instead.

## Required environment variables

`config/settings/production.py` fails fast (raises
`ImproperlyConfigured` at process start) if any of these are missing —
there is no insecure fallback in production, by design:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django cryptographic signing key |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated allowed `Host` headers |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string (cache + Celery broker/result backend) |
| `DOCUMENT_STORAGE_ENDPOINT_URL` / `_ACCESS_KEY` / `_SECRET_KEY` / `_BUCKET` | S3-compatible object storage |
| `INTEGRATION_SECRET_KEY` | Fernet key encrypting webhook/integration secrets at rest |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origin(s) |
| `SENTRY_DSN` | Optional — Sentry stays inert if unset |

`docker-compose.prod.yml` requires every secret-bearing value with no
compose-level fallback, mirroring this fail-loudly posture. Real values
belong in a secrets manager or the hosting platform's env-var injection
— never committed to this repository (`.env` files are gitignored and
for local development only).

## Release steps, in order

1. **Build** all three images (backend, worker reuses the backend image,
   frontend) from the tagged commit.
2. **Run the migration step explicitly, before starting the new
   backend/worker containers**:
   ```bash
   docker compose -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput
   ```
   This is deliberately not baked into the container's start command
   (see the comment above the `backend` service in
   `docker-compose.prod.yml`) — a container that migrates on every
   restart is a correctness/availability risk during a multi-instance
   rolling deploy, and a migration failure should fail the release step
   loudly rather than leave a container crash-looping in a retry loop.
3. **Start** `backend`, `celery-worker`, and `frontend`.
4. **Health-check** the new backend before routing real traffic to it —
   `GET /api/readiness/` (checks Postgres + Redis connectivity, 503 if
   either is unreachable).
5. **Smoke-test**: `GET /api/health/`, `GET /api/readiness/`, the
   frontend's root route, and one client-side route on a hard refresh
   (confirms the nginx SPA fallback, not a 404).
6. **Seed or verify demo data**, if this deployment serves the portfolio
   demo: `python manage.py seed_demo_data` (idempotent — safe to run
   against an already-seeded workspace).

## TLS and reverse proxy

Neither the backend container nor the frontend nginx container
terminates TLS. A real deployment needs a reverse proxy or platform load
balancer in front of both — see
[`docs/security-assumptions.md`](security-assumptions.md).

## Rollback

Because the migration step is explicit and separate from container
start (see step 2 above), rolling back is:

1. **Stop routing traffic** to the new backend/worker/frontend containers
   (revert the load balancer / reverse-proxy target to the previous
   image tag).
2. **Re-point** `backend`, `celery-worker`, and `frontend` at the
   previous image tag and restart them.
3. **Database migrations are the one non-trivial part.** This project's
   migrations are not required to be written as backward-compatible by
   convention (no such policy is currently enforced) — before rolling
   back a release that included a migration, confirm the previous code
   version is still compatible with the *current* (migrated) schema, or
   restore the pre-migration database backup instead (see
   [`docs/operations/backup-recovery.md`](operations/backup-recovery.md)).
   The safest rollback is always "redeploy the previous image without
   touching the database" — only reach for a schema rollback
   (`manage.py migrate <app> <previous_migration_name>`) if the new
   migration is confirmed reversible.
4. **Re-run the smoke test** (step 5 above) against the rolled-back
   deployment before considering the rollback complete.

## Validating this locally

```bash
docker compose -f docker-compose.prod.yml config   # validate/render, no daemon action
docker compose -f docker-compose.prod.yml up --build -d postgres redis minio
docker compose -f docker-compose.prod.yml run --rm minio-init
docker compose -f docker-compose.prod.yml run --rm backend python manage.py migrate --noinput
docker compose -f docker-compose.prod.yml up --build -d backend celery-worker frontend
curl -f http://localhost:${BACKEND_PORT:-8000}/api/health/
curl -f http://localhost:${BACKEND_PORT:-8000}/api/readiness/
curl -f http://localhost:${FRONTEND_PORT:-8080}/
```

See [`docs/limitations.md`](limitations.md) for what "validated" means
here — local Docker Compose validation, not a live deployment that has
received real traffic.
