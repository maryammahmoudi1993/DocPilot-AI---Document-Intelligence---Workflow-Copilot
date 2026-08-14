import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.documents.models import Document
from apps.workspaces.models import Workspace


@pytest.mark.django_db
def test_seed_demo_documents_requires_the_demo_workspace_to_already_exist():
    with pytest.raises(CommandError):
        call_command("seed_demo_documents")


@pytest.mark.django_db
def test_seed_demo_documents_creates_the_sample_invoice_and_contract(fake_storage):
    call_command("seed_demo_data")

    call_command("seed_demo_documents")

    workspace = Workspace.objects.get(slug="demo-workspace")
    documents = Document.objects.filter(workspace=workspace)
    assert documents.count() == 2
    filenames = set(documents.values_list("filename", flat=True))
    assert filenames == {"sample-invoice.pdf", "sample-contract.pdf"}
    for document in documents:
        assert document.storage_key in fake_storage.objects


@pytest.mark.django_db
def test_seed_demo_documents_is_idempotent(fake_storage):
    call_command("seed_demo_data")
    call_command("seed_demo_documents")

    call_command("seed_demo_documents")

    workspace = Workspace.objects.get(slug="demo-workspace")
    assert Document.objects.filter(workspace=workspace).count() == 2
