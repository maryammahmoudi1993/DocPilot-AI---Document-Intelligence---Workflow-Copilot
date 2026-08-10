"""Celery application bootstrap for the async document-processing
pipeline (Phase 4). Kept minimal — no task logic here, only wiring; see
apps/processing/tasks.py for the actual pipeline task.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("docpilot")
# Reuse Django's settings, namespaced under CELERY_ (see
# config/settings/base.py's CELERY_* values) instead of a separate
# Celery-only config file.
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
