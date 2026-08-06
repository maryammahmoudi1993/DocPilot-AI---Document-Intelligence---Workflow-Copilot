from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from apps.accounts.models import User
from apps.audit.services import record_event


def authenticate_user(*, request: Request, email: str, password: str) -> User:
    """Authenticate and record an audit event either way.

    Returns a generic "invalid email or password" error regardless of
    whether the email exists — never reveal account existence to an
    unauthenticated caller.
    """
    user = authenticate(request, email=email, password=password)
    if user is None or not user.is_active:
        record_event(event_type="auth.login_failed", metadata={"email": email})
        raise AuthenticationFailed("Invalid email or password.")

    record_event(event_type="auth.login_succeeded", actor=user)
    return user
