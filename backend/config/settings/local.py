"""Local development settings.

Reads `backend/.env` (gitignored, copy from `.env.example`) if present, then
falls back to the defaults in `base.py`.
"""

import environ

from .base import *  # noqa: F403
from .base import BASE_DIR, env
from .base import SECRET_KEY as _BASE_SECRET_KEY

environ.Env.read_env(str(BASE_DIR / ".env"))

DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# Convenience-only fallback so `manage.py check` works out of the box in a
# fresh checkout. Never used outside local development: production.py
# requires DJANGO_SECRET_KEY to be set and refuses to start otherwise.
SECRET_KEY = _BASE_SECRET_KEY or "django-insecure-local-development-only-key"  # noqa: S105

# Fixed dev-only Fernet key so a fresh checkout works without extra setup
# — never used outside local development (production.py requires a real
# one; see apps/notifications/crypto.py).
INTEGRATION_SECRET_KEY = INTEGRATION_SECRET_KEY or "xjnqLuaWBy-MYTPeJUKpEGiIB1W1VbeMBsyYaPfswhc="  # noqa: F405, S105

# The Docker Compose backend/celery-worker images install tesseract-ocr
# and poppler-utils (see ../../Dockerfile) so real OCR works out of the
# box in local dev — base.py's "mock" default is for contexts (a bare
# `pip install` outside Docker, CI) where those binaries aren't present.
DOCUMENT_OCR_PROVIDER = env.str("DOCUMENT_OCR_PROVIDER", default="tesseract")
