import pytest
from django.urls import reverse

from tests.factories import (
    DocumentFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.mark.django_db
def test_document_detail_includes_a_signed_download_url(api_client, fake_storage):
    workspace = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace)
    document = DocumentFactory(workspace=workspace, storage_key="ws/doc.pdf")
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("document-detail", args=[workspace.id, document.id]))

    assert response.status_code == 200
    assert response.data["download_url"].startswith("https://fake-storage.test/ws/doc.pdf")
    # The private storage key itself is never returned to the client.
    assert "storage_key" not in response.data


@pytest.mark.django_db
def test_signed_url_carries_the_configured_expiry(api_client, fake_storage, settings):
    settings.DOCUMENT_SIGNED_URL_EXPIRY_SECONDS = 120
    workspace = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace)
    document = DocumentFactory(workspace=workspace, storage_key="ws/doc.pdf")
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("document-detail", args=[workspace.id, document.id]))

    assert "expires_in=120" in response.data["download_url"]


@pytest.mark.django_db
def test_document_list_does_not_include_a_signed_url(api_client, fake_storage):
    """Signed URLs are only generated for the detail view (one document,
    one deliberate read) — generating one per row in a list response
    would be wasteful and unnecessary."""
    workspace = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace)
    DocumentFactory(workspace=workspace)
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("document-list", args=[workspace.id]))

    assert response.status_code == 200
    assert "download_url" not in response.data["results"][0]
