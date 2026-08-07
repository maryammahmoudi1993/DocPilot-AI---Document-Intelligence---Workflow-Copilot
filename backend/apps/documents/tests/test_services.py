from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents import services
from apps.documents.models import Document
from tests.factories import UserFactory, WorkspaceFactory


@pytest.mark.django_db
def test_create_document_deletes_the_uploaded_object_if_the_db_row_fails_to_save(fake_storage):
    """No orphaned storage object left behind if the DB half of the
    operation fails after the upload half already succeeded."""
    workspace = WorkspaceFactory()
    user = UserFactory()
    file = SimpleUploadedFile("a.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")

    with patch(
        "apps.documents.models.Document.objects.create", side_effect=RuntimeError("db exploded")
    ):
        with pytest.raises(RuntimeError):
            services.create_document(
                workspace=workspace, uploaded_by=user, uploaded_file=file, storage=fake_storage
            )

    assert fake_storage.objects == {}
    assert Document.objects.count() == 0
