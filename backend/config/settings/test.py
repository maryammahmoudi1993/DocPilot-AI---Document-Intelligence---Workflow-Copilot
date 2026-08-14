"""Test settings.

Runs against a real PostgreSQL (+pgvector) database, not SQLite. Through
Phase 5, this suite used SQLite in-memory for speed and zero setup, since
nothing depended on Postgres-specific behavior. Phase 6 introduces
`DocumentChunk.embedding` (a pgvector column via `pgvector.django.VectorField`)
— a feature SQLite cannot represent at all — so `DATABASES` now inherits
base.py's `DATABASE_URL`-driven Postgres config unconditionally, same as
local/production. Requires a reachable Postgres with the `vector` extension
available (docker-compose's `postgres` service, or the `pgvector/pgvector`
image the CI workflow already runs) — there is no dependency-free fallback
for this app going forward.
"""

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = "django-insecure-test-only-key-at-least-32-bytes-long"  # noqa: S105

ALLOWED_HOSTS = ["testserver"]

# Fast password hashing in tests — never used outside the test settings.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# The real API only registers JSONParser (no multipart/form parsing — see
# base.py), but DRF's test client defaults its request bodies to
# multipart unless told otherwise, which the API would then reject with
# 415. Every real request is JSON, so tests should default to that too.
REST_FRAMEWORK = {**REST_FRAMEWORK, "TEST_REQUEST_DEFAULT_FORMAT": "json"}  # noqa: F405

SENTRY_DSN = ""

LOGGING_CONFIG = None  # keep test output quiet; re-enable per-test if needed

# Celery tasks run synchronously, in-process, in the same transaction as
# the test — no broker/worker needed to test the pipeline.
# CELERY_TASK_EAGER_PROPAGATES is deliberately left at its default
# (False): the pipeline task (apps/processing/tasks.py) intentionally
# catches every exception itself (including the internal `Retry` control-
# flow exception `self.retry()` raises) and never lets one escape
# uncaught — that's what makes a worker process survive an unexpected
# per-document failure. Setting propagate=True here would make Celery's
# eager-mode tracer re-raise that internal Retry exception immediately
# instead of letting `apply()`'s own retry-loop catch it, breaking
# in-test retry simulation entirely (see test_tasks.py's retry tests).
CELERY_TASK_ALWAYS_EAGER = True
DOCUMENT_OCR_PROVIDER = "mock"
# Pinned regardless of any GEMINI_API_KEY / *_PROVIDER value a
# developer's local .env happens to have set — the project rule is that
# unit tests never call a paid provider, and individual tests still
# override these via the `settings` fixture when they need to exercise
# the Gemini-provider code path against a monkeypatched client.
DOCUMENT_CLASSIFICATION_PROVIDER = "keyword"
DOCUMENT_EXTRACTION_PROVIDER = "regex"

# Fixed test-only Fernet key (see apps/notifications/crypto.py) — never
# used outside test settings.
INTEGRATION_SECRET_KEY = "xjnqLuaWBy-MYTPeJUKpEGiIB1W1VbeMBsyYaPfswhc="  # noqa: S105
NOTIFICATION_WEBHOOK_PROVIDER = "mock"
