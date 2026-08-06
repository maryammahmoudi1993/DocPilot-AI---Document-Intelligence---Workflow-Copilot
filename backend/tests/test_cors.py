"""CORS must be configured for the frontend dev server to call the API
cross-origin with credentials (the refresh-token cookie) — see
docs/adr/0003-cors-configuration.md.
"""

from django.urls import reverse


def test_allowed_origin_gets_cors_headers_with_credentials(api_client) -> None:
    response = api_client.get(reverse("health"), HTTP_ORIGIN="http://localhost:3000")

    assert response["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response["Access-Control-Allow-Credentials"] == "true"


def test_disallowed_origin_gets_no_cors_headers(api_client) -> None:
    response = api_client.get(reverse("health"), HTTP_ORIGIN="http://evil.example.com")

    assert "Access-Control-Allow-Origin" not in response
