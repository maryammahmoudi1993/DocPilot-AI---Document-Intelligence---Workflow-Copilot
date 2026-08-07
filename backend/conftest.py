import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _clear_cache():
    """DRF throttling state lives in the cache, not the database, so it
    isn't rolled back by pytest-django's per-test transaction — without
    this, a throttle test could bleed into an unrelated later test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def fake_storage(monkeypatch):
    """Patches apps.documents.services.get_storage_backend so any
    document test — including view-level tests that never inject a
    backend themselves — uses an in-memory fake instead of trying to
    reach real S3/MinIO."""
    from apps.documents.tests.fakes import FakeStorageBackend

    backend = FakeStorageBackend()
    monkeypatch.setattr("apps.documents.services.get_storage_backend", lambda: backend)
    return backend
