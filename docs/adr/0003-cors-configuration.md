# ADR-0003: CORS via an explicit origin allowlist, not a wildcard

Status: Accepted
Date: 2026-08-06

## Context

The frontend (`localhost:3000` in dev) and backend (`localhost:8000`)
are different origins. The auth design (ADR-0002, Phase 2A) puts the
refresh token in an httpOnly cookie, which browsers only send
cross-origin if the server explicitly allows credentialed requests from
that exact origin — CORS's default is to deny this, and a wildcard
(`Access-Control-Allow-Origin: *`) is not permitted alongside
credentials at all (the spec forbids it).

## Decision

`django-cors-headers`, configured with `CORS_ALLOWED_ORIGINS` (an
explicit, environment-driven list — defaults to `http://localhost:3000`
for local dev) and `CORS_ALLOW_CREDENTIALS = True`. No wildcard, ever.

## Consequences

**Easier:** the frontend can call the API with `credentials: 'include'`
and the refresh cookie round-trips correctly.

**Harder:** every real frontend origin (staging, production) must be
added to `CORS_ALLOWED_ORIGINS` explicitly via the `CORS_ALLOWED_ORIGINS`
env var — this is a deliberate cost, not an oversight; an unlisted
origin is correctly refused.

## Alternatives considered

**Same-origin deployment (reverse-proxy the frontend and API under one
domain)**: legitimate for production and would remove the need for CORS
entirely, but doesn't help local development, where the Vite dev server
and Django dev server are always separate processes/ports. CORS
configuration is needed regardless; this ADR doesn't preclude also
same-origin-proxying in production later.

**`CORS_ALLOW_ALL_ORIGINS = True`**: rejected outright — incompatible
with `CORS_ALLOW_CREDENTIALS = True` per the CORS spec, and would be a
real security regression even if the library permitted it.
