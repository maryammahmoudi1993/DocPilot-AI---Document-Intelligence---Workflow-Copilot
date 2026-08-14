# Known Limitations

Stated honestly, per this project's own rule against faking working
behavior in the final demo. Nothing here is a defect being hidden — it's
scope this portfolio project deliberately did not cover, or a tradeoff
made explicit rather than silently assumed.

## Providers are mock/deterministic by default

- **OCR** defaults to a deterministic mock (`DOCUMENT_OCR_PROVIDER=mock`);
  a real Tesseract-based provider exists and is used in local Docker
  Compose (`tesseract-ocr` + `poppler-utils` in the backend image) but
  accuracy on real scanned documents was never benchmarked — treat OCR
  output as illustrative of the *pipeline*, not of production-grade OCR
  quality.
- **Classification** is a deterministic keyword heuristic, not a trained
  model or LLM call.
- **RAG embeddings and answers** use a mock provider — no real
  Anthropic/OpenAI-style API key is configured anywhere in this project.
  This was a deliberate scope decision (see `docs/adr/`), not an
  oversight: wiring a real LLM/embedding provider behind the existing
  `apps/assistant/providers.py` interface is a bounded follow-up, not a
  redesign.
- **Extraction confidence scores** are illustrative — explicitly labeled
  as such in the Analytics UI — not a calibrated accuracy metric derived
  from a real ground-truth evaluation set.

## Malware scanning is a signature check, not a general AV engine

See [`docs/security-assumptions.md`](security-assumptions.md) — the
default `EicarSignatureScanProvider` only recognizes the EICAR
antivirus test file. Real malware detection requires wiring a real
engine behind the existing `MalwareScanProvider` interface.

## No distributed rate limiting

DRF's cache-backed throttling works per-process. A horizontally-scaled
deployment needs to confirm its `CACHES` backend is shared (e.g. Redis)
for throttle counts to hold across instances — not verified under load
in this project.

## Dependency vulnerability scanning is manual

No Dependabot/Snyk-equivalent automated scan runs in this repository's
CI. `pip-audit`/`npm audit` can be run manually; neither is a required
CI gate.

## Live end-to-end (browser + real backend + real queue) coverage is partial

The Playwright suite covers rendering, keyboard operability, and
route/component-level behavior against a running frontend dev server.
The single deterministic 12-step "upload → processing → review →
approval → RAG → workflow → webhook → audit → analytics" flow described
in the Phase 11 scope is implemented as a spec
(`frontend/e2e/complete-demo-flow.spec.ts`) but its full run against a
live backend + Celery worker + seeded demo documents was validated
manually against a locally running Docker Compose stack rather than
wired into CI as a required, always-green gate — CI's frontend job runs
against MSW-mocked network responses, matching the pattern already used
for `sign-in.spec.ts` and the rest of the existing Playwright suite.
Making the full live flow a CI-required gate (spinning up backend +
worker + Postgres + Redis + MinIO inside GitHub Actions) is a real,
bounded follow-up, not started here.

## Branch protection / required-status enforcement is advisory, not applied

The commands each CI workflow runs (`ruff`, `mypy`, `pytest`, `npm run
lint/typecheck/test/build`, etc.) are documented as the required gates
in this repository's working agreements, but turning "PR merge blocked
until these pass" into an actually-enforced GitHub branch-protection
rule requires repository-admin access to GitHub's web UI (Settings →
Branches) that isn't available through this environment's tooling — see
[`docs/operations/release-checklist.md`](operations/release-checklist.md)
for the one-time manual step to close this gap.

## No malware/virus real-world benchmark, no load/perf testing

Route-level code splitting and bundle-size budgets are measured (see
[`docs/adr/0005-route-level-code-splitting.md`](adr/0005-route-level-code-splitting.md)),
but there is no load-testing (concurrent users, sustained upload
throughput, Celery queue depth under load) anywhere in this project.

## Sample documents are synthetic

The bundled sample invoice/contract fixtures used by the demo seed
command are synthetically generated for this project, not real business
documents — see their own provenance note in
[`backend/apps/documents/fixtures/README.md`](../backend/apps/documents/fixtures/README.md).

## No production deployment has actually received real traffic

This is a portfolio demonstration. "Deployment validated" in this
project's release notes means the production Docker images build, boot,
and pass health checks locally with `docker-compose.prod.yml` — it does
not mean the application has been deployed to a live host and observed
under real usage.
