import pytest
from django.urls import reverse

from apps.documents.models import Document
from tests.factories import (
    DocumentFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.mark.django_db
def test_anonymous_cannot_list_documents(api_client):
    workspace = WorkspaceFactory()

    response = api_client.get(reverse("document-list", args=[workspace.id]))

    assert response.status_code == 401


@pytest.mark.django_db
def test_user_cannot_list_documents_in_a_workspace_they_are_not_a_member_of(api_client):
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace_a)
    api_client.force_authenticate(user=user)

    response = api_client.get(reverse("document-list", args=[workspace_b.id]))

    assert response.status_code == 403


@pytest.mark.django_db
def test_document_detail_404s_for_a_document_in_a_different_workspace(api_client):
    """A document_id that's real, but belongs to another workspace, must
    not be reachable through this workspace's URL (IDOR check)."""
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace_a)
    foreign_document = DocumentFactory(workspace=workspace_b)
    api_client.force_authenticate(user=user)

    response = api_client.get(
        reverse("document-detail", args=[workspace_a.id, foreign_document.id])
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_member_can_archive_a_document(api_client, fake_storage):
    workspace = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace)
    document = DocumentFactory(workspace=workspace)
    api_client.force_authenticate(user=user)

    response = api_client.post(reverse("document-archive", args=[workspace.id, document.id]))

    assert response.status_code == 200
    document.refresh_from_db()
    assert document.status == "archived"


@pytest.mark.django_db
def test_non_member_cannot_archive_a_document(api_client, fake_storage):
    workspace = WorkspaceFactory()
    document = DocumentFactory(workspace=workspace)
    outsider = UserFactory()
    api_client.force_authenticate(user=outsider)

    response = api_client.post(reverse("document-archive", args=[workspace.id, document.id]))

    assert response.status_code == 403
    document.refresh_from_db()
    assert document.status == "uploaded"


@pytest.mark.django_db
def test_member_can_delete_a_document_and_its_storage_object(api_client, fake_storage):
    workspace = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace)
    document = DocumentFactory(workspace=workspace, storage_key="ws/doc.pdf")
    fake_storage.objects["ws/doc.pdf"] = b"content"
    api_client.force_authenticate(user=user)

    response = api_client.delete(reverse("document-detail", args=[workspace.id, document.id]))

    assert response.status_code == 204
    assert not Document.objects.filter(id=document.id).exists()
    assert "ws/doc.pdf" not in fake_storage.objects


@pytest.mark.django_db
def test_non_member_cannot_delete_a_document(api_client, fake_storage):
    workspace = WorkspaceFactory()
    document = DocumentFactory(workspace=workspace)
    outsider = UserFactory()
    api_client.force_authenticate(user=outsider)

    response = api_client.delete(reverse("document-detail", args=[workspace.id, document.id]))

    assert response.status_code == 403
    assert Document.objects.filter(id=document.id).exists()
