# ADR-0004: S3-compatible object storage behind a narrow interface

Status: Accepted
Date: 2026-08-07

## Context

Uploaded documents (Phase 3) need durable, private binary storage —
not something a relational database is well suited for. Files must
never be publicly reachable; the only access path is a short-lived
signed URL generated per request. Local development has no real S3
account, and the project shouldn't require one just to run `docker
compose up`.

Separately, storage code needs to be unit-testable without a network
call to real object storage, and without pulling in a mocking library
that turned out to be broken on this project's development platform
(`moto[s3]` fails to install on Windows due to a long-path limitation
in one of its vendored dependencies).

## Decision

- Define a narrow `StorageBackend` Protocol (`upload`, `generate_presigned_url`,
  `delete`) in `apps/documents/storage.py`. All of `apps/documents/services.py`
  depends only on this interface, never on boto3 directly.
- One concrete implementation, `S3StorageBackend`, backed by boto3
  against any S3-compatible endpoint. Locally that's MinIO (see
  `docker-compose.yml`); in deployment it's real S3 (or another
  S3-compatible provider) — swapped entirely through
  `DOCUMENT_STORAGE_*` settings, no code change.
- Two boto3 clients, not one. Uploads/deletes happen from the backend
  process itself, which (when running via `docker compose`) reaches
  MinIO over the internal Docker network hostname
  (`DOCUMENT_STORAGE_ENDPOINT_URL=http://minio:9000`). A presigned URL,
  by contrast, is handed to the browser, which cannot resolve that
  internal hostname — it only has the host-mapped port
  (`http://localhost:9000`). Signing with the wrong endpoint produces a
  URL that silently fails to connect for the user. `S3StorageBackend`
  builds a second client against `DOCUMENT_STORAGE_PUBLIC_ENDPOINT_URL`
  when that setting is non-empty, and reuses the same client for both
  purposes otherwise (the common case when running the backend natively,
  outside Docker, where there's only one reachable endpoint).
- Files are never public. Reading one back always goes through
  `generate_presigned_url`, expiry controlled by
  `DOCUMENT_SIGNED_URL_EXPIRY_SECONDS` and decided by the caller
  (`services.get_document_signed_url`), not by the storage backend
  itself — keeping the backend Django-settings-agnostic.
- Tests mock the boto3 client directly (`unittest.mock`), and a
  hand-rolled `FakeStorageBackend` test double (in-memory dict) stands
  in for the whole interface in service/view-level tests, rather than
  using a mocking library like moto.

## Consequences

**Easier:** switching storage providers (MinIO → S3 → another
S3-compatible provider) is a settings change, not a code change.
Storage-dependent code is fully unit-testable with no real network
calls and no container/service dependency at test time. The
Docker-networking presigned-URL bug (internal hostname baked into a
browser-facing URL) is structurally prevented rather than left as a
footgun.

**Harder:** two client objects to reason about instead of one; the
dual-endpoint setting is an easy thing to forget when adding a new
deployment environment (self-hosted, another cloud) — it must be
revisited whenever the browser-reachable and backend-reachable
endpoints diverge. The `FakeStorageBackend` test double duplicates
(by hand) the behavioral contract of `S3StorageBackend`, so a
behavior change to one must be mirrored in the other or tests can
pass while the real backend silently disagrees with the fake.

## Alternatives considered

**Store files directly on local/container disk (`FileSystemStorage`
or Django's default `FileField`):** simplest to stand up, but doesn't
model production at all — real deployment isn't going to keep
documents on a single container's ephemeral filesystem — and provides
no natural mechanism for time-limited private access; would need to be
thrown away and rebuilt for deployment rather than incrementally
extended.

**`django-storages`:** a reasonable general-purpose choice, but this
project intentionally keeps a hand-written, narrow interface
(`StorageBackend`) rather than a general storage framework — this app
only ever needs three operations (upload, sign, delete), so the extra
surface area and its own abstraction-over-abstraction cost weren't
worth it. Revisit if storage needs grow beyond documents (e.g.
static/media file serving) and the duplication starts to hurt.

**`moto[s3]` for test mocking:** the natural choice for S3 testing, but
its install failed on this project's development platform (Windows
`MAX_PATH` limitation hit by a vendored dependency in
`moto.stepfunctions`, unrelated to the S3 module actually needed).
Rather than fight the platform, storage tests mock boto3 directly and
higher-level tests use a hand-rolled `FakeStorageBackend`. Worth
revisiting moto (or an alternative) if the fake's duplicated contract
becomes a maintenance burden.
