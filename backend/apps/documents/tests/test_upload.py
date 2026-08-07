import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.documents.models import Document
from tests.factories import UserFactory, WorkspaceFactory, WorkspaceMembershipFactory

PDF_BYTES = b"%PDF-1.4\n%mock pdf content for tests\n"


def pdf_file(name="invoice.pdf", content=PDF_BYTES, content_type="application/pdf"):
    return SimpleUploadedFile(name, content, content_type=content_type)


@pytest.fixture
def member_client(api_client):
    workspace = WorkspaceFactory()
    user = UserFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace)
    api_client.force_authenticate(user=user)
    return api_client, workspace, user


@pytest.mark.django_db
def test_valid_upload_succeeds_and_is_stored_privately(member_client, fake_storage):
    api_client, workspace, user = member_client

    response = api_client.post(
        reverse("document-list", args=[workspace.id]), {"file": pdf_file()}, format="multipart"
    )

    assert response.status_code == 201
    assert response.data["filename"] == "invoice.pdf"
    assert response.data["status"] == "uploaded"
    document = Document.objects.get(id=response.data["id"])
    # The object exists in storage under its private key — never a
    # public URL, and the key is never itself returned to the client.
    assert document.storage_key in fake_storage.objects
    assert "storage_key" not in response.data


@pytest.mark.django_db
def test_upload_creates_an_audit_event(member_client, fake_storage):
    api_client, workspace, user = member_client

    api_client.post(
        reverse("document-list", args=[workspace.id]), {"file": pdf_file()}, format="multipart"
    )

    assert AuditEvent.objects.filter(event_type="document.uploaded", workspace=workspace).exists()


@pytest.mark.django_db
def test_invalid_extension_is_rejected(member_client, fake_storage):
    api_client, workspace, user = member_client

    response = api_client.post(
        reverse("document-list", args=[workspace.id]),
        {
            "file": SimpleUploadedFile(
                "malware.exe", b"MZ...", content_type="application/octet-stream"
            )
        },
        format="multipart",
    )

    assert response.status_code == 400
    assert response.data["error"]["code"] == "validation_error"
    assert fake_storage.objects == {}


@pytest.mark.django_db
def test_mime_mismatch_is_rejected(member_client, fake_storage):
    api_client, workspace, user = member_client

    response = api_client.post(
        reverse("document-list", args=[workspace.id]),
        {"file": pdf_file(name="invoice.pdf", content_type="image/png")},
        format="multipart",
    )

    assert response.status_code == 400
    assert fake_storage.objects == {}


@pytest.mark.django_db
def test_content_signature_mismatch_is_rejected(member_client, fake_storage):
    """Declared type and extension both say PDF, but the actual bytes
    aren't a PDF — caught by the magic-byte check."""
    api_client, workspace, user = member_client

    response = api_client.post(
        reverse("document-list", args=[workspace.id]),
        {"file": pdf_file(content=b"not actually a pdf")},
        format="multipart",
    )

    assert response.status_code == 400
    assert fake_storage.objects == {}


@pytest.mark.django_db
def test_oversized_file_is_rejected(member_client, fake_storage, settings):
    api_client, workspace, user = member_client
    settings.DOCUMENT_MAX_UPLOAD_SIZE_BYTES = 10

    response = api_client.post(
        reverse("document-list", args=[workspace.id]), {"file": pdf_file()}, format="multipart"
    )

    assert response.status_code == 400
    assert fake_storage.objects == {}


@pytest.mark.django_db
def test_duplicate_checksum_within_workspace_is_rejected(member_client, fake_storage):
    api_client, workspace, user = member_client
    api_client.post(
        reverse("document-list", args=[workspace.id]), {"file": pdf_file()}, format="multipart"
    )

    response = api_client.post(
        reverse("document-list", args=[workspace.id]),
        {"file": pdf_file(name="invoice-copy.pdf")},
        format="multipart",
    )

    assert response.status_code == 400
    assert "existing_document_id" in response.data["error"]["details"]
    assert Document.objects.filter(workspace=workspace).count() == 1


@pytest.mark.django_db
def test_identical_content_is_allowed_in_a_different_workspace(fake_storage, api_client):
    """Duplicate detection is workspace-scoped, not global — the same
    invoice uploaded to two different customers' workspaces is not a
    'duplicate'."""
    user = UserFactory()
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    WorkspaceMembershipFactory(user=user, workspace=workspace_a)
    WorkspaceMembershipFactory(user=user, workspace=workspace_b)
    api_client.force_authenticate(user=user)

    first = api_client.post(
        reverse("document-list", args=[workspace_a.id]), {"file": pdf_file()}, format="multipart"
    )
    second = api_client.post(
        reverse("document-list", args=[workspace_b.id]), {"file": pdf_file()}, format="multipart"
    )

    assert first.status_code == 201
    assert second.status_code == 201


@pytest.mark.django_db
def test_upload_without_a_file_is_rejected(member_client, fake_storage):
    api_client, workspace, user = member_client

    response = api_client.post(
        reverse("document-list", args=[workspace.id]), {}, format="multipart"
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_anonymous_cannot_upload(api_client, fake_storage):
    workspace = WorkspaceFactory()

    response = api_client.post(
        reverse("document-list", args=[workspace.id]), {"file": pdf_file()}, format="multipart"
    )

    assert response.status_code == 401
