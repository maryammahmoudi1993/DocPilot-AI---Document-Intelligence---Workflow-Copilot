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
