from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.health.services import DependencyStatus


def test_health_endpoint_returns_ok(api_client) -> None:
    response = api_client.get(reverse("health"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_endpoint_ok_when_dependencies_reachable(api_client) -> None:
    with patch(
        "apps.health.views.get_readiness_statuses",
        return_value=[
            DependencyStatus(name="database", ok=True),
            DependencyStatus(name="redis", ok=True),
        ],
    ):
        response = api_client.get(reverse("readiness"))

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "checks": {"database": {"ok": True}, "redis": {"ok": True}},
    }


@pytest.mark.django_db
def test_readiness_endpoint_returns_503_when_a_dependency_is_down(api_client) -> None:
    with patch(
        "apps.health.views.get_readiness_statuses",
        return_value=[
            DependencyStatus(name="database", ok=True),
            DependencyStatus(name="redis", ok=False, error="connection refused"),
        ],
    ):
        response = api_client.get(reverse("readiness"))

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["checks"]["redis"]["ok"] is False
    # Internal error detail must never reach the client.
    assert "error" not in body["checks"]["redis"]
    assert "connection refused" not in response.content.decode()


@pytest.mark.django_db
def test_readiness_database_check_uses_real_connection(api_client) -> None:
    """Exercises the real (test-database-backed) database check path once,
    so the SQL round trip itself is verified, not just the mock plumbing."""
    from apps.health.services import check_database

    with patch(
        "apps.health.views.get_readiness_statuses",
        return_value=[check_database()],
    ):
        response = api_client.get(reverse("readiness"))

    assert response.json()["checks"]["database"]["ok"] is True
