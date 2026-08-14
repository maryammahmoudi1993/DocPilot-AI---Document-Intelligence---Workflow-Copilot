# DocPilot AI — Document Intelligence & Workflow Copilot

**Portfolio demonstration project.** Upload invoices, contracts, receipts,
reports, policies, and forms; parse/OCR them; classify document type;
extract structured data with confidence scoring; review and correct
low-confidence fields; approve; index for semantic search; ask grounded
RAG questions with citations; run approval/automation workflows; trigger
notifications and webhooks; keep an immutable audit trail; view
operational analytics. Any metrics, integrations, or workflows shown are
**sample data** / **illustrative** / **simulated** unless stated
otherwise — this is not a claim of production usage, customer results,
or certified accuracy. See [`docs/limitations.md`](docs/limitations.md)
for what's honestly out of scope.

Licensed under the [MIT License](LICENSE).

## Architecture

A single Django/DRF **modular monolith** backend + a single React/TS
frontend, with asynchronous background processing via Celery/Redis. No
microservices — see [`docs/architecture-overview.md`](docs/architecture-overview.md)
(module map, request flow, an entity-relationship diagram, and a
sequence diagram of the primary demo flow) and
[`docs/adr/0001-modular-monolith.md`](docs/adr/0001-modular-monolith.md)
for the reasoning.

```
frontend/               React + TypeScript + Vite
backend/                Django + DRF (config/, apps/, common/, tests/)
docker-compose.yml       Local dev: PostgreSQL (pgvector), Redis, MinIO, backend, celery-worker
docker-compose.prod.yml  Production-parity manifest: gunicorn, worker, nginx-served frontend
```

## Prerequisites

- Python 3.12
- Node.js 18+ and npm 9+
- Docker + Docker Compose

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

# Infrastructure (PostgreSQL + Redis + MinIO + backend + worker)
cp .env.example .env
docker compose up
```

At that point: backend on `http://localhost:8000` (`/api/health/`,
`/api/readiness/`, `/api/schema/docs/`), frontend dev server via
`cd frontend && npm run dev` (`http://localhost:3000`).

Seed a deterministic demo workspace (idempotent, safe to re-run):

```bash
cd backend && python manage.py seed_demo_data
```

Prints the demo password for the seeded users (`owner@demo.docpilot.ai`,
`admin@…`, `finance@…`, `reviewer@…`, `viewer@…`) to stdout — a
portfolio-demo credential documented on purpose, not a real secret.

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
per-module breakdown, and [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for
the production-specific required variables.

## Common commands

**Backend** (`cd backend`):
```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py migrate
python manage.py runserver
python manage.py seed_demo_data      # deterministic demo workspace, idempotent
python manage.py reset_demo_data     # clear + rebuild the demo workspace's data, idempotent
ruff check .
ruff format --check .
mypy .
pytest --cov
python manage.py spectacular --file schema.yaml   # OpenAPI schema
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
docker compose config                        # validate/render the compose file
docker compose up                             # start postgres, redis, minio, backend, celery-worker
docker compose up -d postgres redis minio     # infra only, run backend natively instead
docker compose down -v                        # stop and remove volumes (destroys local DB/Redis/MinIO data)

# Production-parity image build/validation — see docs/DEPLOYMENT.md
docker compose -f docker-compose.prod.yml config
docker compose -f docker-compose.prod.yml up --build
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
docker compose -f docker-compose.prod.yml config
git status --short   # should be clean
```

See [`docs/operations/release-checklist.md`](docs/operations/release-checklist.md)
for the full pre-merge and pre-deployment checklist, and
[`docs/limitations.md`](docs/limitations.md) for the one gap in this
list that's still manual: turning these into an enforced GitHub
branch-protection rule requires one-time repository-admin action outside
this project's own tooling.

## Documentation

| Doc | Covers |
|---|---|
| [`docs/architecture-overview.md`](docs/architecture-overview.md) | Module map, request flow, ER diagram, primary-flow sequence diagram |
| [`docs/security-assumptions.md`](docs/security-assumptions.md) | What's enforced vs. assumed, trust boundaries |
| [`docs/limitations.md`](docs/limitations.md) | Known gaps, stated honestly |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Production images, required config, release steps, rollback |
| [`docs/operations/backup-recovery.md`](docs/operations/backup-recovery.md) | Backup approach and recovery process |
| [`docs/operations/release-checklist.md`](docs/operations/release-checklist.md) | Pre-merge and pre-deployment checklist |
| [`docs/portfolio-case-study.md`](docs/portfolio-case-study.md) | The engineering narrative for this project as a portfolio piece |
| [`docs/demo-script.md`](docs/demo-script.md) | A 60–90 second guided walkthrough |
| [`docs/adr/`](docs/adr/) | Individual architectural decisions |

## Status

All phases through **Phase 11 (production release)** are implemented —
authentication/workspaces/RBAC, document upload + secure storage, async
processing (OCR/classification), extraction + review/correction,
approval workflow, RAG assistant, visual workflow automation, approvals/
notifications/webhooks/audit, dashboard/analytics/settings, a landing
page, security/accessibility/performance hardening, and production
Docker images. See [`docs/architecture-overview.md`](docs/architecture-overview.md)
for the module-by-module breakdown and [`docs/limitations.md`](docs/limitations.md)
for what's explicitly out of scope rather than silently missing.

## Third-party attribution

- Design reference mockups under `design-reference/` (gitignored, local
  reference only — never shipped as the production application) and
  their `support.js` runtime are treated as generated reference assets,
  not edited or redistributed.
- Font: [Plus Jakarta Sans](https://fonts.google.com/specimen/Plus+Jakarta+Sans)
  (Open Font License). Icons: [Lucide](https://lucide.dev/) (ISC
  License). Neither is vendored into this repository — both are pulled
  as normal package/CDN dependencies per their own licenses.
