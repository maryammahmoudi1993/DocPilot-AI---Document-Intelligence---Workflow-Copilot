"""Dependency checks used by the readiness endpoint.

Kept out of the view (see the project's rule keeping business/system logic
out of views) so it can be unit-tested and mocked without spinning up a
real database/Redis connection in every test.
"""

from dataclasses import dataclass

import redis
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    ok: bool
    error: str | None = None


def check_database() -> DependencyStatus:
    try:
        connection = connections["default"]
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except OperationalError as exc:
        return DependencyStatus(name="database", ok=False, error=str(exc))
    return DependencyStatus(name="database", ok=True)


def check_redis() -> DependencyStatus:
    try:
        client = redis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        client.ping()
    except redis.RedisError as exc:
        return DependencyStatus(name="redis", ok=False, error=str(exc))
    return DependencyStatus(name="redis", ok=True)


def get_readiness_statuses() -> list[DependencyStatus]:
    return [check_database(), check_redis()]
