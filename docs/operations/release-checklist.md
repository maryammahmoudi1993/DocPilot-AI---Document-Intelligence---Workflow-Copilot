# Release Checklist

Run through before merging a phase branch to `main`, and again before
cutting a real deployment.

## Before merging to `main`

- [ ] Tree is clean (`git status`).
- [ ] Backend: `ruff check .`, `ruff format --check .`, `mypy .`,
      `python manage.py check`, `python manage.py makemigrations --check
      --dry-run`, `pytest` — all clean.
- [ ] Backend: `python manage.py spectacular --file /tmp/schema.yaml`
      generates without error (pre-existing enum-naming warnings are
      known and tracked, not new errors).
- [ ] Frontend: `npm run lint`, `npm run typecheck`, `npm run test`,
      `npm run build` — all clean.
- [ ] Frontend: relevant Playwright specs pass; no new console errors or
      unhandled promise rejections in the suite's output.
- [ ] `docker compose config` and `docker compose -f
      docker-compose.prod.yml config` both render without error.
- [ ] No secrets in the diff (`git diff` review — `.env` files stay
      gitignored, no hardcoded credentials, no API keys).
- [ ] Migrations are committed with the model change that requires them,
      not as a separate follow-up commit.
- [ ] Commit messages are Conventional Commits, one logical concern
      each — no `update`/`fix stuff`/`final`.
- [ ] README(s) updated if behavior changed.
- [ ] New/changed architectural decisions have an ADR under `docs/adr/`.

## Before a real deployment (in addition to the above)

- [ ] All required production environment variables are set in the
      target environment (see [`docs/DEPLOYMENT.md`](../DEPLOYMENT.md)'s
      table) — none are placeholder/example values.
- [ ] `DJANGO_SECRET_KEY` and `INTEGRATION_SECRET_KEY` are freshly
      generated for this deployment, not reused from `.env.example` or
      a previous environment.
- [ ] A database backup exists from immediately before this release —
      see [`docs/operations/backup-recovery.md`](backup-recovery.md).
- [ ] The images build successfully from the release commit
      (`docker compose -f docker-compose.prod.yml build`).
- [ ] Migration step run and confirmed successful **before** starting
      the new backend/worker containers (see the release steps in
      `docs/DEPLOYMENT.md`).
- [ ] `/api/health/` and `/api/readiness/` both return 200 on the new
      deployment before traffic is routed to it.
- [ ] Frontend smoke test: root route loads, a client-side route
      survives a hard refresh (SPA fallback working).
- [ ] Rollback plan confirmed reachable (previous image tag still
      available, previous-schema compatibility checked if this release
      included a migration) — see `docs/DEPLOYMENT.md`'s Rollback
      section.
- [ ] TLS/reverse-proxy in front of both the backend and frontend
      containers is configured and verified (neither container
      terminates TLS itself).

## Branch-protection gate (one-time, manual, GitHub Settings)

This repository's CI workflows (`.github/workflows/backend-ci.yml`,
`.github/workflows/frontend-ci.yml`) define the required checks, but
turning them into an actually-enforced "PR cannot merge until these
pass" rule requires a repository admin to configure GitHub branch
protection (Settings → Branches → require status checks) — not
something achievable from this environment's tooling (no `gh` CLI
token with admin scope is configured here). Until that one-time step is
done by the repository owner, treat the CI gate as advisory: contributors
are expected to have run these checks locally before merging, exactly as
if the platform were enforcing it. See
[`docs/limitations.md`](../limitations.md).
