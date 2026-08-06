"""Every DRF-routed error response uses the stable
`{"error": {"code", "message", ...}}` envelope — see common/exceptions.py.
"""

from django.urls import reverse


def test_method_not_allowed_uses_stable_error_envelope(api_client) -> None:
    response = api_client.post(reverse("health"))

    assert response.status_code == 405
    body = response.json()
    assert body["error"]["code"] == "method_not_allowed"
    assert isinstance(body["error"]["message"], str)
