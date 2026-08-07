import pytest
from django.urls import reverse

from apps.documents.models import Document, DocumentStatus
from tests.factories import (
    DocumentFactory,
    UserFactory,
    WorkspaceFactory,
    WorkspaceMembershipFactory,
)


@pytest.fixture
def member_client(api_client):
    workspace = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace)
    api_client.force_authenticate(user=user)
    return api_client, workspace


@pytest.mark.django_db
def test_bulk_archive_archives_every_requested_document(member_client, fake_storage):
    api_client, workspace = member_client
    documents = DocumentFactory.create_batch(3, workspace=workspace)

    response = api_client.post(
        reverse("document-bulk-archive", args=[workspace.id]),
        {"document_ids": [str(d.id) for d in documents]},
    )

    assert response.status_code == 200
    assert Document.objects.filter(workspace=workspace, status=DocumentStatus.ARCHIVED).count() == 3


@pytest.mark.django_db
def test_bulk_archive_is_all_or_nothing_when_an_id_is_unknown(member_client, fake_storage):
    """Safe bulk operations: every id must belong to this workspace, or
    none of them are mutated — not "archive the valid ones and ignore
    the rest", which would silently hide a caller's mistake (or an
    attempt to probe another workspace's ids)."""
    api_client, workspace = member_client
    real_document = DocumentFactory(workspace=workspace)
    foreign_document = DocumentFactory(workspace=WorkspaceFactory())

    response = api_client.post(
        reverse("document-bulk-archive", args=[workspace.id]),
        {"document_ids": [str(real_document.id), str(foreign_document.id)]},
    )

    assert response.status_code == 400
    real_document.refresh_from_db()
    assert real_document.status == DocumentStatus.UPLOADED


@pytest.mark.django_db
def test_bulk_delete_removes_every_requested_document_and_its_storage_object(
    member_client, fake_storage
):
    api_client, workspace = member_client
    documents = DocumentFactory.create_batch(2, workspace=workspace)
    for document in documents:
        fake_storage.objects[document.storage_key] = b"content"

    response = api_client.post(
        reverse("document-bulk-delete", args=[workspace.id]),
        {"document_ids": [str(d.id) for d in documents]},
    )

    assert response.status_code == 204
    assert Document.objects.filter(workspace=workspace).count() == 0
    assert fake_storage.objects == {}


@pytest.mark.django_db
def test_bulk_delete_is_all_or_nothing_when_an_id_is_unknown(member_client, fake_storage):
    api_client, workspace = member_client
    real_document = DocumentFactory(workspace=workspace)
    fake_storage.objects[real_document.storage_key] = b"content"

    response = api_client.post(
        reverse("document-bulk-delete", args=[workspace.id]),
        {"document_ids": [str(real_document.id), "00000000-0000-0000-0000-000000000000"]},
    )

    assert response.status_code == 400
    assert Document.objects.filter(id=real_document.id).exists()
    assert real_document.storage_key in fake_storage.objects


@pytest.mark.django_db
def test_non_member_cannot_bulk_delete(api_client, fake_storage):
    workspace = WorkspaceFactory()
    document = DocumentFactory(workspace=workspace)
    outsider = UserFactory()
    api_client.force_authenticate(user=outsider)

    response = api_client.post(
        reverse("document-bulk-delete", args=[workspace.id]), {"document_ids": [str(document.id)]}
    )

    assert response.status_code == 403
    assert Document.objects.filter(id=document.id).exists()
