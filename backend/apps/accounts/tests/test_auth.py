import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from tests.factories import (
    DEFAULT_PASSWORD,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.mark.django_db
def test_login_succeeds_and_sets_httponly_refresh_cookie(api_client):
    user = UserFactory()

    response = api_client.post(
        reverse("auth-login"), {"email": user.email, "password": DEFAULT_PASSWORD}
    )

    assert response.status_code == 200
    assert "access" in response.data
    assert response.data["user"]["email"] == user.email
    # The access token must never come back in a cookie, and the refresh
    # token must never be readable by frontend JS.
    assert "refresh_token" in response.cookies
    assert response.cookies["refresh_token"]["httponly"]
    assert "refresh" not in response.data


@pytest.mark.django_db
@pytest.mark.parametrize(
    "credentials",
    [
        pytest.param({"email": "nobody@example.com", "password": "whatever"}, id="unknown-email"),
        pytest.param(None, id="wrong-password"),
    ],
)
def test_login_failure_is_generic_and_does_not_reveal_account_existence(api_client, credentials):
    if credentials is None:
        user = UserFactory()
        credentials = {"email": user.email, "password": "wrong-password"}

    response = api_client.post(reverse("auth-login"), credentials)

    assert response.status_code == 401
    assert response.data["error"]["code"] == "authentication_failed"
    assert response.data["error"]["message"] == "Invalid email or password."


@pytest.mark.django_db
def test_anonymous_request_to_session_is_denied(api_client):
    response = api_client.get(reverse("auth-session"))

    assert response.status_code == 401
    assert response.data["error"]["code"] == "not_authenticated"


@pytest.mark.django_db
def test_invalid_bearer_token_is_rejected(api_client):
    api_client.credentials(HTTP_AUTHORIZATION="Bearer not-a-real-token")

    response = api_client.get(reverse("auth-session"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_session_returns_current_user_and_their_workspaces(api_client):
    user = UserFactory()
    workspace = WorkspaceFactory()
    membership = WorkspaceMembershipFactory(user=user, workspace=workspace, role="admin")
    user.active_workspace = workspace
    user.save(update_fields=["active_workspace"])
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("auth-session"))

    assert response.status_code == 200
    assert response.data["user"]["email"] == user.email
    assert response.data["active_workspace_id"] == str(workspace.id)
    assert response.data["workspaces"] == [
        {
            "id": str(workspace.id),
            "name": workspace.name,
            "slug": workspace.slug,
            "role": membership.role,
        }
    ]


@pytest.mark.django_db
def test_refresh_issues_a_new_access_token_from_the_cookie(api_client):
    user = UserFactory()
    api_client.post(reverse("auth-login"), {"email": user.email, "password": DEFAULT_PASSWORD})

    response = api_client.post(reverse("auth-refresh"))

    assert response.status_code == 200
    assert "access" in response.data


@pytest.mark.django_db
def test_refresh_without_a_cookie_fails(api_client):
    response = api_client.post(reverse("auth-refresh"))

    assert response.status_code == 401


@pytest.mark.django_db
def test_logout_blacklists_the_refresh_token_so_it_cannot_be_reused(api_client):
    user = UserFactory()
    login_response = api_client.post(
        reverse("auth-login"), {"email": user.email, "password": DEFAULT_PASSWORD}
    )
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")

    logout_response = api_client.post(reverse("auth-logout"))
    assert logout_response.status_code == 204

    # The refresh cookie set at login is still attached to this client;
    # using it again after logout must fail (blacklisted).
    refresh_response = api_client.post(reverse("auth-refresh"))
    assert refresh_response.status_code == 401


@pytest.mark.django_db
def test_login_is_throttled_after_too_many_attempts(api_client):
    user = UserFactory()

    responses = [
        api_client.post(reverse("auth-login"), {"email": user.email, "password": "wrong"})
        for _ in range(11)
    ]

    assert responses[-1].status_code == 429
    assert responses[-1].data["error"]["code"] == "throttled"


@pytest.mark.django_db
def test_login_success_and_failure_both_create_audit_events(api_client):
    user = UserFactory()

    api_client.post(reverse("auth-login"), {"email": user.email, "password": DEFAULT_PASSWORD})
    api_client.post(reverse("auth-login"), {"email": user.email, "password": "wrong"})

    event_types = list(AuditEvent.objects.values_list("event_type", flat=True))
    assert "auth.login_succeeded" in event_types
    assert "auth.login_failed" in event_types
