"""Document business logic — upload, archive, delete, bulk operations,
signed URLs. Kept out of views/serializers (non-negotiable project
rule) so it's independently unit-testable and every mutation goes
through the same transactional, audit-logged path.
"""

import hashlib
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.documents.models import Document, DocumentStatus
from apps.documents.storage import StorageBackend, get_storage_backend
from apps.documents.validation import validate_upload
from apps.processing.services import enqueue_processing
from apps.workspaces.models import Workspace
from common.logging import correlation_id_var


def compute_sha256(uploaded_file) -> str:
    """Streams the file in chunks (Django's UploadedFile.chunks()) rather
    than reading it all into memory at once — safe for the largest files
    this app accepts."""
    hasher = hashlib.sha256()
    uploaded_file.seek(0)
    for chunk in uploaded_file.chunks():
        hasher.update(chunk)
    uploaded_file.seek(0)
    return hasher.hexdigest()


def _build_storage_key(*, workspace_id, filename: str) -> str:
    extension = Path(filename).suffix.lower()
    return f"{workspace_id}/{uuid.uuid4()}{extension}"


def create_document(
    *,
    workspace: Workspace,
    uploaded_by,
    uploaded_file,
    storage: StorageBackend | None = None,
) -> Document:
    storage = storage or get_storage_backend()

    validate_upload(uploaded_file)
    checksum = compute_sha256(uploaded_file)

    # Duplicate policy (workspace-scoped): an archived document with the
    # same checksum doesn't block a re-upload — only an active one does.
    duplicate = (
        Document.objects.filter(workspace=workspace, checksum_sha256=checksum)
        .exclude(status=DocumentStatus.ARCHIVED)
        .first()
    )
    if duplicate is not None:
        raise ValidationError(
            {
                "file": "A document with identical content already exists in this workspace.",
                "existing_document_id": str(duplicate.id),
            }
        )

    storage_key = _build_storage_key(workspace_id=workspace.id, filename=uploaded_file.name)
    content_type = uploaded_file.content_type or "application/octet-stream"
    storage.upload(key=storage_key, fileobj=uploaded_file, content_type=content_type)

    try:
        with transaction.atomic():
            document = Document.objects.create(
                workspace=workspace,
                uploaded_by=uploaded_by,
                filename=uploaded_file.name,
                content_type=content_type,
                size_bytes=uploaded_file.size,
                checksum_sha256=checksum,
                storage_key=storage_key,
            )
            record_event(
                event_type="document.uploaded",
                actor=uploaded_by,
                workspace=workspace,
                metadata={"document_id": str(document.id), "filename": document.filename},
            )
            # Deliberately inside the same atomic block (so it only ever
            # fires for a document row that actually committed) but the
            # task itself isn't scheduled until after commit — see
            # enqueue_processing. Upload returns as soon as this
            # function returns; processing runs later, out of this
            # request entirely (Phase 4 requirement).
            enqueue_processing(document=document, correlation_id=correlation_id_var.get() or "")
            # Best-effort: a workflow-dispatch failure must never block
            # or roll back a successful upload.
            try:
                from apps.workflows.services import dispatch_event

                dispatch_event(
                    workspace_id=str(workspace.id),
                    event="document_uploaded",
                    context={"event": "document_uploaded", "document_id": str(document.id)},
                )
            except Exception:  # noqa: BLE001 - see comment above
                pass
    except Exception:
        # The DB row never committed — don't leave an orphaned object in
        # storage with nothing referencing it.
        storage.delete(key=storage_key)
        raise

    return document


def archive_document(*, document: Document, actor) -> Document:
    if document.status == DocumentStatus.ARCHIVED:
        raise ValidationError({"status": "Document is already archived."})

    with transaction.atomic():
        document.status = DocumentStatus.ARCHIVED
        document.archived_at = timezone.now()
        document.save(update_fields=["status", "archived_at"])
        record_event(
            event_type="document.archived",
            actor=actor,
            workspace=document.workspace,
            metadata={"document_id": str(document.id)},
        )
    return document


def delete_document(*, document: Document, actor, storage: StorageBackend | None = None) -> None:
    storage = storage or get_storage_backend()
    storage_key = document.storage_key
    workspace = document.workspace

    with transaction.atomic():
        record_event(
            event_type="document.deleted",
            actor=actor,
            workspace=workspace,
            metadata={"document_id": str(document.id), "filename": document.filename},
        )
        document.delete()
    # Only after the DB delete has committed — an orphaned storage object
    # (if this call fails) is a smaller problem than a DB row pointing at
    # storage that's already gone.
    storage.delete(key=storage_key)


def get_document_signed_url(*, document: Document, storage: StorageBackend | None = None) -> str:
    storage = storage or get_storage_backend()
    return storage.generate_presigned_url(
        key=document.storage_key, expires_in=settings.DOCUMENT_SIGNED_URL_EXPIRY_SECONDS
    )


def _resolve_bulk_targets(*, workspace: Workspace, document_ids) -> list[Document]:
    documents = list(Document.objects.filter(workspace=workspace, id__in=document_ids))
    found_ids = {document.id for document in documents}
    missing = set(document_ids) - found_ids
    if missing:
        # All-or-nothing: an id that isn't real (or belongs to another
        # workspace) blocks the whole batch rather than silently
        # skipping it — a caller who typo'd or is probing another
        # workspace's ids gets a clear error, not partial success.
        raise ValidationError(
            {"document_ids": f"Unknown document ids: {sorted(str(i) for i in missing)}"}
        )
    return documents


def bulk_archive(*, workspace: Workspace, document_ids, actor) -> list[Document]:
    documents = _resolve_bulk_targets(workspace=workspace, document_ids=document_ids)
    with transaction.atomic():
        for document in documents:
            if document.status != DocumentStatus.ARCHIVED:
                document.status = DocumentStatus.ARCHIVED
                document.archived_at = timezone.now()
                document.save(update_fields=["status", "archived_at"])
                record_event(
                    event_type="document.archived",
                    actor=actor,
                    workspace=workspace,
                    metadata={"document_id": str(document.id)},
                )
    return documents


def bulk_delete(
    *, workspace: Workspace, document_ids, actor, storage: StorageBackend | None = None
) -> None:
    storage = storage or get_storage_backend()
    documents = _resolve_bulk_targets(workspace=workspace, document_ids=document_ids)
    storage_keys = [document.storage_key for document in documents]
    document_ids_found = [document.id for document in documents]

    with transaction.atomic():
        for document in documents:
            record_event(
                event_type="document.deleted",
                actor=actor,
                workspace=workspace,
                metadata={"document_id": str(document.id), "filename": document.filename},
            )
        Document.objects.filter(id__in=document_ids_found).delete()

    for key in storage_keys:
        storage.delete(key=key)
