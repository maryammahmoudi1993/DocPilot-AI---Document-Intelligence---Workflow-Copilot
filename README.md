# DocPilot AI — Document Intelligence & Workflow Copilot

**Portfolio demonstration project.** Upload invoices, contracts, receipts,
reports, policies, and forms; parse/OCR them; extract structured data with
confidence scoring; review and correct low-confidence fields; approve;
index for semantic search; ask grounded RAG questions with citations;
run approval/automation workflows; trigger notifications and webhooks;
keep an immutable audit trail; view operational analytics. Any metrics,
integrations, or workflows shown are **sample data** / **illustrative** /
**simulated** unless stated otherwise — this is not a claim of production
usage, customer results, or certified accuracy.

## Architecture

A single Django/DRF **modular monolith** backend + a single React/TS
frontend, with asynchronous background processing via Celery/Redis (not
yet implemented — see the phase status below). No microservices — see
[`docs/architecture-overview.md`](docs/architecture-overview.md) and
[`docs/adr/0001-modular-monolith.md`](docs/adr/0001-modular-monolith.md)
for the full picture and reasoning.

```
frontend/   React + TypeScript + Vite
backend/    Django + DRF (config/, apps/, common/, tests/)
docker-compose.yml   PostgreSQL (pgvector) + Redis + backend, for local dev
```

## Prerequisites

- Python 3.12
- Node.js 18+ and npm 9+
- Docker + Docker Compose (for PostgreSQL/Redis; see caveat below)

## Clean-clone setup

```bash
git clone <this repo>
cd docpilot-ai

# Backend
cd backend
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env        # fill in real values (a working local default already lets `manage.py check` pass)
cd ..

# Frontend
cd frontend
npm install
cp .env.example .env
cd ..

# Infrastructure (PostgreSQL + Redis + backend)
cp .env.example .env
docker compose up
```

At that point: backend on `http://localhost:8000` (`/api/health/`,
`/api/readiness/`, `/api/schema/docs/`), frontend dev server via
`cd frontend && npm run dev`.

See [`backend/README.md`](backend/README.md) and
[`frontend/README.md`](frontend/README.md) for the full command
reference for each project, including a Windows-specific `npm run`
workaround if your checkout path contains an unescaped `&`.

## Environment configuration

Three `.env.example` files, one per concern — copy each to `.env`
(gitignored) and fill in real values:

| File | Used by |
|---|---|
| `.env.example` (root) | `docker compose up` |
| `backend/.env.example` | Running the backend directly (outside Docker) |
| `frontend/.env.example` | The frontend dev server / build |

Settings are environment-based throughout
(`backend/config/settings/{base,local,test,production}.py`) — nothing
environment-specific is hardcoded. See `backend/README.md` for the
per-module breakdown.

## Common commands

**Backend** (`cd backend`):
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py runserver
ruff check .
ruff format --check .
mypy .
pytest --cov
```

**Frontend** (`cd frontend`):
```bash
npm run dev
npm run build
npm run lint
npm run typecheck
npm run test
npm run test:e2e
```

**Docker Compose** (repo root):
```bash
docker compose config      # validate/render the compose file
docker compose up          # start postgres, redis, backend
docker compose up -d postgres redis   # infra only, run backend natively instead
docker compose down -v     # stop and remove volumes (destroys local DB/Redis data)
```

## Validation commands

The same commands CI runs (see `.github/workflows/`):

```bash
# Backend
cd backend && ruff check . && ruff format --check . && mypy . \
  && python manage.py check && python manage.py makemigrations --check --dry-run \
  && pytest --cov && python manage.py spectacular --file /tmp/schema.yaml --validate

# Frontend
cd frontend && npm run lint && npm run typecheck && npm run test && npm run build

# Repository
docker compose config
git status --short   # should be clean
```

## Known limitation: Docker daemon in this development sandbox

`docker compose config` (pure YAML rendering, no daemon needed) works and
is verified. Actually starting the containers and confirming the
healthchecks pass end-to-end was **not** verified in the sandbox this
phase was built in — the Docker CLI is present but its daemon
(`dockerDesktopLinuxEngine`) wasn't reachable from that shell. The
compose file follows standard, previously-verified patterns
(`pg_isready` / `redis-cli ping` healthchecks, named volumes,
`depends_on: condition: service_healthy`) and CI (`.github/workflows/backend-ci.yml`)
runs equivalent postgres/redis service containers on every push, which
*does* exercise real connectivity. Verify locally with
`docker compose up` on a machine with a working Docker daemon before
relying on this for a live demo.

## Status

- **Phase 0A** — repository audit, design-reference preservation. Done.
- **Phase 0B** — backend foundation (Django/DRF, health/readiness,
  structured logging, error envelope). Done.
- **Phase 0C** — frontend foundation (Vite/React/TS, routing, quality
  tooling). Done.
- **Phase 0D** — this phase: Docker Compose, CI, root docs, ADR.
- No business features (auth, documents, extraction, RAG, workflows,
  analytics) are implemented yet — see `docs/architecture-overview.md`
  for the module map and what's planned per phase.
