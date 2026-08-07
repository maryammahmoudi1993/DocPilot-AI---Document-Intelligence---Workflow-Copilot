"""Shared settings for all environments.

Environment-specific modules (`local.py`, `test.py`, `production.py`) import
`*` from this module and override only what genuinely differs. Every value
that varies by environment (secrets, hosts, debug flags, database/broker
URLs) is read from the process environment via `django-environ` — nothing
environment-specific is hardcoded here.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env()

# SECURITY WARNING: keep the production secret key out of version control.
# Each environment module is responsible for deciding where its .env file
# (if any) is read from and for enforcing that required variables are set.
SECRET_KEY = env.str("DJANGO_SECRET_KEY", default="")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "apps.health",
    "apps.accounts",
    "apps.workspaces",
    "apps.audit",
    "apps.documents",
]

# Custom user model, defined before any migration has ever been applied to
# a real database in this project (see docs/adr/0002-custom-user-model.md)
# — the safe time to introduce one is before the first `migrate`, not after.
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "common.middleware.CorrelationIdMiddleware",
    # Must come before CommonMiddleware per django-cors-headers' own docs.
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# --- Database -----------------------------------------------------------
# PostgreSQL (with pgvector once vector-backed models are introduced) is the
# only supported production/local target. DATABASE_URL follows the standard
# `postgres://USER:PASSWORD@HOST:PORT/NAME` scheme.
DATABASES = {
    "default": env.db_url(
        "DATABASE_URL",
        default="postgres://docpilot:docpilot@localhost:5432/docpilot",
    ),
}

# --- CORS -----------------------------------------------------------------
# The frontend runs on a different origin in dev (localhost:3000 vs the
# backend's localhost:8000) and must send/receive the httpOnly
# refresh-token cookie, which requires explicit allow-listing — CORS
# defaults to denying credentialed cross-origin requests. See
# docs/adr/0003-cors-configuration.md.
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=["http://localhost:3000"])
CORS_ALLOW_CREDENTIALS = True

# --- Redis ----------------------------------------------------------------
# Connection settings only in this phase — no Celery app/tasks are defined
# yet (that lands in the async-processing phase). Used now by the
# readiness endpoint to verify Redis is reachable.
REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")

# --- Object storage (documents) --------------------------------------------
# S3-compatible everywhere — MinIO locally (see docker-compose.yml),
# real S3 (or another S3-compatible provider) in deployment. Never
# public: files are fetched only via short-lived signed URLs generated
# per request (see apps/documents/storage.py).
DOCUMENT_STORAGE_ENDPOINT_URL = env.str(
    "DOCUMENT_STORAGE_ENDPOINT_URL", default="http://localhost:9000"
)
# Only needed when DOCUMENT_STORAGE_ENDPOINT_URL isn't reachable by the
# browser (running via docker-compose: the backend reaches MinIO at the
# internal hostname http://minio:9000, but a presigned URL must use the
# host-mapped http://localhost:9000 or the browser can't resolve it).
# Empty (the default) means "same as DOCUMENT_STORAGE_ENDPOINT_URL" — the
# common case when running the backend natively, not via Docker.
DOCUMENT_STORAGE_PUBLIC_ENDPOINT_URL = env.str("DOCUMENT_STORAGE_PUBLIC_ENDPOINT_URL", default="")
DOCUMENT_STORAGE_ACCESS_KEY = env.str("DOCUMENT_STORAGE_ACCESS_KEY", default="docpilot")
DOCUMENT_STORAGE_SECRET_KEY = env.str("DOCUMENT_STORAGE_SECRET_KEY", default="docpilot-dev-secret")
DOCUMENT_STORAGE_BUCKET = env.str("DOCUMENT_STORAGE_BUCKET", default="docpilot-documents")
DOCUMENT_STORAGE_REGION = env.str("DOCUMENT_STORAGE_REGION", default="us-east-1")
# MinIO needs virtual-host-style addressing disabled (path style) since
# it doesn't do per-bucket DNS the way real S3 does.
DOCUMENT_STORAGE_USE_PATH_STYLE = env.bool("DOCUMENT_STORAGE_USE_PATH_STYLE", default=True)

DOCUMENT_MAX_UPLOAD_SIZE_BYTES = env.int("DOCUMENT_MAX_UPLOAD_SIZE_BYTES", default=20 * 1024 * 1024)
DOCUMENT_SIGNED_URL_EXPIRY_SECONDS = env.int("DOCUMENT_SIGNED_URL_EXPIRY_SECONDS", default=300)

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization -------------------------------------------------
LANGUAGE_CODE = "en-us"
# All timestamps are stored and reasoned about in UTC internally; conversion
# to a user's local time zone happens at the presentation layer only.
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# --- DRF --------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.stable_exception_handler",
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        # Deliberately tight — authentication endpoints are the highest-value
        # brute-force target in the whole API.
        "auth-login": "10/min",
        "auth-refresh": "30/min",
    },
}

# Access tokens are short-lived and meant for the Authorization header
# (in-memory frontend storage only — see frontend auth phase). Refresh
# tokens are longer-lived, rotated on every use, and blacklisted on
# rotation/logout (token_blacklist app) so a stolen refresh token has a
# bounded window of usefulness even if never explicitly revoked.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "DocPilot AI API",
    "DESCRIPTION": (
        "Portfolio demonstration API for DocPilot AI — document intelligence "
        "and workflow automation. Demo workspace / sample data."
    ),
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --- Logging ----------------------------------------------------------
# Structured (JSON-shaped) logging so log lines are machine-parseable and
# carry a request correlation ID (see common.middleware.CorrelationIdMiddleware
# and common.logging.CorrelationIdFilter). Never log secrets, tokens,
# passwords, full document contents, or extracted field values — see
# common/logging.py for the enforced-at-the-edges rationale.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "correlation_id": {"()": "common.logging.CorrelationIdFilter"},
    },
    "formatters": {
        "structured": {
            "()": "common.logging.StructuredFormatter",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
            "filters": ["correlation_id"],
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env.str("DJANGO_LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

# --- Error reporting (Sentry) ------------------------------------------
# No-op unless SENTRY_DSN is set. Wired here (rather than deferred) because
# it is part of the project's required infrastructure direction and has no
# behavioral cost when disabled.
SENTRY_DSN = env.str("SENTRY_DSN", default="")
