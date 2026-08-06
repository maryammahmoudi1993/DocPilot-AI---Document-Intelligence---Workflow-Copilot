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

SECRET_KEY = "django-insecure-test-only-key"  # noqa: S105

ALLOWED_HOSTS = ["testserver"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# Fast password hashing in tests — never used outside the test settings.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

SENTRY_DSN = ""

LOGGING_CONFIG = None  # keep test output quiet; re-enable per-test if needed
