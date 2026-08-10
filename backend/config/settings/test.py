"""Test settings.

Documented deviation from the production/local target (PostgreSQL): this
phase has no models yet, so nothing depends on Postgres- or pgvector-
specific behavior. Using SQLite in-memory keeps the unit test suite fast
and dependency-free (no database server required to run `pytest`). Once a
model that needs a Postgres-only feature (e.g. a pgvector column) is
introduced, that app's tests must switch to a real Postgres test database
(e.g. via a docker-compose/CI service) — do not assume SQLite compatibility
project-wide.
"""

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = "django-insecure-test-only-key-at-least-32-bytes-long"  # noqa: S105

ALLOWED_HOSTS = ["testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

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
# the test — no broker/worker needed to test the pipeline. Propagate
# exceptions so a task bug fails the test loudly instead of being
# swallowed. Never use real OCR (no tesseract-ocr binary in CI/dev
# without Docker) — see apps/processing/providers.py.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
DOCUMENT_OCR_PROVIDER = "mock"
