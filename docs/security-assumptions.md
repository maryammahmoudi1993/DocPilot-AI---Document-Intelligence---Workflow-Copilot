# Security Assumptions

What this application actually enforces, and what it assumes about its
environment instead of enforcing — written for anyone deciding whether
to trust this codebase's patterns for something beyond a portfolio demo.

## What's enforced in code (verified, not aspirational)

- **Workspace isolation.** Every workspace-scoped endpoint re-derives the
  caller's role from a real `WorkspaceMembership` row on every request
  (`apps/workspaces/permissions.py`) — never from a client-supplied
  header, cookie, or the user's `active_workspace` convenience pointer.
  A resource ID belonging to another workspace 404s rather than 403ing
  (no existence leak). Covered by a consolidated cross-workspace +
  anonymous authorization-matrix test across representative endpoints
  (`apps/*/tests/test_isolation.py` and the Phase 10 matrix test).
- **JWT auth.** Short-lived access token (15 min, header-only, kept in
  memory by the frontend — never `localStorage`). Refresh token (7 days)
  lives only in an httpOnly, `SameSite`-scoped cookie; rotated and the
  old one blacklisted on every refresh. Auth endpoints are throttled.
- **Upload validation.** Extension, declared MIME type, size, and (where
  a reliable signature exists) file-content magic bytes are all checked
  before a file is trusted — see `apps/documents/validation.py`. A
  malware-scanning interface (`apps/documents/scanning.py`) additionally
  rejects uploads matching the industry-standard EICAR test signature by
  default; see its own docstring for what it does and does not claim to
  catch (below).
- **Object storage.** Files are never public. The only way to read one
  back is a short-lived signed URL generated per request
  (`DOCUMENT_SIGNED_URL_EXPIRY_SECONDS`, default 300s).
- **Secrets at rest.** Webhook/integration secrets are encrypted with
  Fernet before being stored (`apps/notifications/crypto.py`) and are
  never returned through any API response, including to the workspace
  owner who set them.
- **Webhook integrity.** Outbound webhook payloads are HMAC-SHA256
  signed; delivery is idempotent (a delivery-attempt record + idempotency
  key prevent double-firing on retry).
- **Audit immutability.** `apps.audit` exposes a read-only list API only
  — there is no update/delete endpoint anywhere in the app, and no other
  app writes to `AuditEvent` except through `apps.audit.services.record_event`.
- **Log redaction.** `common.logging.StructuredFormatter` redacts `extra`
  values whose key matches password/token/secret/api_key/authorization/
  credential, as a defense-in-depth safety net — callers are still
  primarily responsible for never passing those fields in the first
  place.
- **Security headers & cookies (production settings).** HSTS, `nosniff`,
  `X-Frame-Options`, `Referrer-Policy`, secure+httpOnly+SameSite cookies —
  see `config/settings/production.py`.
- **Untrusted-data handling.** Document text, OCR output, extracted
  values, webhook payloads, and AI/RAG output are all treated as
  untrusted — never interpolated into a prompt or template in a way that
  lets extracted content act as an instruction, never trusted for
  authorization decisions, always validated before use.

## What this project assumes about its environment (documented, not silently relied on)

- **TLS termination.** The application does not terminate TLS itself.
  `docker-compose.prod.yml` and `backend/Dockerfile.prod` assume a
  reverse proxy / load balancer in front of them handles HTTPS — see
  [`docs/operations/deployment.md`](operations/deployment.md).
- **The malware-scanning default is a signature check, not a general AV
  engine.** `EicarSignatureScanProvider` (the default
  `DOCUMENT_MALWARE_SCAN_PROVIDER`) only recognizes the EICAR antivirus
  test file — the same file every commercial AV product uses to verify a
  scanning path works, chosen deliberately because it requires no paid
  service and is safe to exercise in unit tests. It does **not** detect
  real malware. `apps/documents/scanning.py`'s `MalwareScanProvider`
  Protocol is the extension point a real engine (ClamAV via `clamd`, a
  hosted scanning API) would be wired in behind for any deployment that
  needs real malware detection.
- **Rate limiting is per-process, not distributed.** DRF's built-in
  throttling (used on auth endpoints) is cache-backed; a multi-instance
  deployment needs a shared cache backend (Redis, already in the stack)
  for throttle counts to be consistent across instances — verify the
  `CACHES` backend before assuming throttling holds under horizontal
  scaling.
- **Database and object-storage credentials are assumed to be managed
  outside this repository** (a secrets manager, platform env-var
  injection) in any real deployment — `.env` files are for local
  development only and are gitignored; `docker-compose.prod.yml`
  requires every secret-bearing variable with no insecure fallback.
- **No WAF / DDoS layer is included.** This is an application-level
  security posture, not a network-perimeter one; a production deployment
  in front of real traffic should sit behind whatever edge protection
  the hosting platform provides.
- **Dependency vulnerability scanning is manual, not continuous.** See
  [`docs/limitations.md`](limitations.md) — no automated Dependabot/
  Snyk-equivalent is configured in this repository's CI.

## Prompt-injection posture (RAG / assistant)

`apps.assistant` treats document text and OCR output as untrusted
content that is retrieved and shown to the model as *data*, not as
instructions — the system prompt and the retrieved-chunk content are
kept in clearly separated roles in every provider call, and the mock
provider used in tests exercises this boundary without a real LLM call
(project rule: unit tests never call a paid LLM provider). This reduces,
but does not eliminate, the risk of instruction-like text embedded in an
uploaded document influencing model output — treat any RAG answer as
requiring the same human review any AI output would.

## Reporting a concern

This is a portfolio project with no production users or real data. If
you're evaluating it and find something concerning, the intended next
step is the repository's issue tracker, not a private disclosure
process (nothing here handles real user data, so there's no live
exposure to coordinate around).
