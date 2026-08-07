from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

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
def test_list_only_returns_the_requested_workspaces_documents(member_client):
    api_client, workspace = member_client
    DocumentFactory.create_batch(2, workspace=workspace)
    DocumentFactory(workspace=WorkspaceFactory())  # a different workspace

    response = api_client.get(reverse("document-list", args=[workspace.id]))

    assert response.status_code == 200
    assert response.data["count"] == 2


@pytest.mark.django_db
def test_list_is_paginated(member_client):
    api_client, workspace = member_client
    DocumentFactory.create_batch(3, workspace=workspace)

    response = api_client.get(reverse("document-list", args=[workspace.id]), {"page_size": 2})

    assert response.data["count"] == 3
    assert len(response.data["results"]) == 2
    assert response.data["next"] is not None


@pytest.mark.django_db
def test_list_can_be_filtered_by_status(member_client):
    api_client, workspace = member_client
    DocumentFactory(workspace=workspace, status=DocumentStatus.UPLOADED)
    DocumentFactory(workspace=workspace, status=DocumentStatus.ARCHIVED)

    response = api_client.get(reverse("document-list", args=[workspace.id]), {"status": "archived"})

    assert response.data["count"] == 1
    assert response.data["results"][0]["status"] == "archived"


@pytest.mark.django_db
def test_list_can_be_searched_by_filename(member_client):
    api_client, workspace = member_client
    DocumentFactory(workspace=workspace, filename="q3-invoice.pdf")
    DocumentFactory(workspace=workspace, filename="contract.pdf")

    response = api_client.get(reverse("document-list", args=[workspace.id]), {"search": "invoice"})

    assert response.data["count"] == 1
    assert response.data["results"][0]["filename"] == "q3-invoice.pdf"


@pytest.mark.django_db
def test_list_can_be_sorted_by_size(member_client):
    api_client, workspace = member_client
    DocumentFactory(workspace=workspace, filename="small.pdf", size_bytes=100)
    DocumentFactory(workspace=workspace, filename="large.pdf", size_bytes=9000)

    response = api_client.get(
        reverse("document-list", args=[workspace.id]), {"ordering": "size_bytes"}
    )

    filenames = [item["filename"] for item in response.data["results"]]
    assert filenames == ["small.pdf", "large.pdf"]


@pytest.mark.django_db
def test_list_defaults_to_newest_first(member_client):
    api_client, workspace = member_client
    older = DocumentFactory(workspace=workspace, filename="older.pdf")
    newer = DocumentFactory(workspace=workspace, filename="newer.pdf")
    # auto_now_add can land both rows in the same SQLite-resolution
    # instant when created back-to-back — force an unambiguous gap
    # rather than relying on real-clock timing in the test.
    Document.objects.filter(id=older.id).update(created_at=timezone.now() - timedelta(days=1))

    response = api_client.get(reverse("document-list", args=[workspace.id]))

    ids = [item["id"] for item in response.data["results"]]
    assert ids == [str(newer.id), str(older.id)]
