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
    """Patches every module-qualified `get_storage_backend` lookup
    (apps.documents.services and apps.processing.tasks — the two places
    that read a document's actual bytes) so any test — including
    view-level and pipeline-level tests that never inject a backend
    themselves — uses one shared in-memory fake instead of trying to
    reach real S3/MinIO. Sharing one fake instance means a document
    uploaded in a test's setup is immediately readable by the
    processing pipeline in the same test."""
    from apps.documents.tests.fakes import FakeStorageBackend

    backend = FakeStorageBackend()
    monkeypatch.setattr("apps.documents.services.get_storage_backend", lambda: backend)
    monkeypatch.setattr("apps.processing.tasks.get_storage_backend", lambda: backend)
    return backend
