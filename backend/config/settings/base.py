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
    "apps.processing",
    "apps.extraction",
    "apps.assistant",
]

# The installed rest_framework_simplejwt.token_blacklist wheel's model
# Meta has drifted from its own shipped migrations (harmless — ordering/
# verbose_name only, no schema change) and, separately, this environment's
# copy of that package was missing migrations/__init__.py entirely (a
# packaging defect that made Django treat the whole app as unmigrated and
# fall back to unordered syncdb — fatal against Postgres's strict FK
# validation, though invisible under SQLite). Redirecting to a
# project-owned, version-controlled copy of the same migration history
# (config/vendor_apps/token_blacklist/migrations/) fixes both: migrations
# are always discoverable regardless of the installed wheel's contents,
# and the Meta drift gets a normal migration instead of failing
# `makemigrations --check` forever. The nested .../migrations/ path
# (rather than pointing straight at token_blacklist/) is deliberate: it's
# what lets this directory fall under the project's existing "**/migrations"
# ruff/mypy/coverage exclude patterns without adding new ones.
MIGRATION_MODULES = {
    "token_blacklist": "config.vendor_apps.token_blacklist.migrations",
}

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

# --- Redis / Celery --------------------------------------------------------
# Redis is both the readiness endpoint's dependency check target and the
# Celery broker/result backend for the async document-processing pipeline
# (Phase 4) — one Redis instance, two roles, no need for a second service.
REDIS_URL = env.str("REDIS_URL", default="redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "UTC"
# Surfaces a "started" state (not just pending/success/failure) for the
# progress/status endpoint — see apps/processing/views.py.
CELERY_TASK_TRACK_STARTED = True

# --- Document processing pipeline ------------------------------------------
# "tesseract" (real OCR — requires the tesseract-ocr and poppler-utils
# system packages installed alongside it; see Dockerfile) or "mock"
# (deterministic, no system dependency — the default here so this module
# stays importable/runnable anywhere without those binaries; local dev
# via Docker Compose overrides to "tesseract", see local.py and
# docker-compose.yml). See apps/processing/providers.py.
DOCUMENT_OCR_PROVIDER = env.str("DOCUMENT_OCR_PROVIDER", default="mock")

# A PDF page yielding fewer extracted characters than this is treated as
# not having a usable digital text layer (i.e. scanned) and routed to
# OCR instead. Deliberately small and documented rather than tuned
# against real scan samples — see known limitations in the Phase 4
# completion report.
DOCUMENT_MIN_DIGITAL_TEXT_CHARS = env.int("DOCUMENT_MIN_DIGITAL_TEXT_CHARS", default=20)

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

# --- RAG knowledge assistant (Phase 6) ---------------------------------
# "mock" (deterministic, no network — the only option wired in this
# phase) or "openai"/"anthropic"-style real providers a future phase
# could add behind the same interface (see apps/assistant/providers.py).
# No real embedding/LLM API key is configured in this project yet — see
# docs/adr for the rationale; mock providers are also what keeps this
# app's tests free of paid-provider calls.
RAG_EMBEDDING_PROVIDER = env.str("RAG_EMBEDDING_PROVIDER", default="mock")
RAG_GENERATION_PROVIDER = env.str("RAG_GENERATION_PROVIDER", default="mock")
# Dimensionality of the mock embedding vectors — arbitrary but fixed
# (changing it requires a migration, since pgvector columns are
# fixed-width). Small on purpose: this is a demo-scale corpus, not a
# production embedding index.
RAG_EMBEDDING_DIMENSIONS = env.int("RAG_EMBEDDING_DIMENSIONS", default=256)
# Chunk size (chars) and retrieval fan-out.
RAG_CHUNK_SIZE_CHARS = env.int("RAG_CHUNK_SIZE_CHARS", default=800)
RAG_RETRIEVAL_TOP_K = env.int("RAG_RETRIEVAL_TOP_K", default=5)
# Cosine distance (0 = identical, 2 = opposite) above which a retrieved
# chunk is considered too dissimilar to ground an answer — see
# apps/assistant/services.answer_question's insufficient-evidence path.
RAG_MAX_GROUNDING_DISTANCE = env.float("RAG_MAX_GROUNDING_DISTANCE", default=0.9)
# Total characters of retrieved chunk text handed to the generation
# provider for one answer — the documented token budget (see
# apps/assistant/services.build_context).
RAG_CONTEXT_BUDGET_CHARS = env.int("RAG_CONTEXT_BUDGET_CHARS", default=6000)

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
