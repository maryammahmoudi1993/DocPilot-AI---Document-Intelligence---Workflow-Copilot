"""Every DRF-routed error response uses the stable
`{"error": {"code", "message", ...}}` envelope — see common/exceptions.py.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.urls import reverse

from common.exceptions import stable_exception_handler


def test_method_not_allowed_uses_stable_error_envelope(api_client) -> None:
    response = api_client.post(reverse("health"))

    assert response.status_code == 405
    body = response.json()
    assert body["error"]["code"] == "method_not_allowed"
    assert isinstance(body["error"]["message"], str)


def test_django_validation_error_is_converted_not_500d() -> None:
    """DRF's default handler auto-converts Django's PermissionDenied and
    Http404 but not Django's ValidationError — a service layer that
    raises the Django one (see apps/workspaces/services.py) must still
    get a 400, not fall through to the generic 500 path."""
    exc = DjangoValidationError({"email": "This user is already a member of the workspace."})

    response = stable_exception_handler(exc, {"view": None})

    assert response is not None
    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
