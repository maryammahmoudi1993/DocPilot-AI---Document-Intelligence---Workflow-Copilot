# Makes the Celery app available as `config.celery_app` so `@shared_task`
# (used throughout apps/processing/tasks.py) binds to it automatically —
# the standard Django+Celery bootstrap pattern.
from .celery import app as celery_app

__all__ = ("celery_app",)
