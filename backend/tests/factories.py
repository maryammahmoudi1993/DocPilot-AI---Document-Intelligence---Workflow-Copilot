import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.approvals.models import ApprovalRequest
from apps.assistant.models import Conversation, DocumentChunk
from apps.documents.models import Document
from apps.extraction.models import DocumentExtraction, ExtractedField, ExtractionStatus
from apps.notifications.models import Notification, WebhookEndpoint
from apps.processing.models import ProcessingJob, ProcessingStage
from apps.workflows.models import Workflow
from apps.workspaces.models import Role, Workspace, WorkspaceMembership

DEFAULT_PASSWORD = "test-pass-only-123!"  # noqa: S105 - fixture-only, not a real credential


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    # Mirrors UserManager._create_user's convention (username defaults to
    # email) — the model doesn't go through that manager method when
    # factory_boy calls Model.objects.create() directly, so it has to be
    # set explicitly here or every factory-created user gets the same
    # blank username and collides on its unique constraint.
    username = factory.LazyAttribute(lambda o: o.email)
    first_name = "Test"
    last_name = "User"

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save(update_fields=["password"])


class WorkspaceFactory(DjangoModelFactory):
    class Meta:
        model = Workspace

    name = factory.Sequence(lambda n: f"Workspace {n}")
    slug = factory.Sequence(lambda n: f"workspace-{n}")


class WorkspaceMembershipFactory(DjangoModelFactory):
    class Meta:
        model = WorkspaceMembership

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    role = Role.VIEWER


class DocumentFactory(DjangoModelFactory):
    class Meta:
        model = Document

    workspace = factory.SubFactory(WorkspaceFactory)
    uploaded_by = factory.SubFactory(UserFactory)
    filename = factory.Sequence(lambda n: f"document-{n}.pdf")
    content_type = "application/pdf"
    size_bytes = 1024
    checksum_sha256 = factory.Sequence(lambda n: f"{n:064x}")
    storage_key = factory.LazyAttribute(lambda o: f"{o.workspace.id}/{o.filename}")


class ProcessingJobFactory(DjangoModelFactory):
    class Meta:
        model = ProcessingJob

    document = factory.SubFactory(DocumentFactory)
    workspace = factory.LazyAttribute(lambda o: o.document.workspace)
    stage = ProcessingStage.QUEUED


class DocumentExtractionFactory(DjangoModelFactory):
    class Meta:
        model = DocumentExtraction

    document = factory.SubFactory(DocumentFactory)
    workspace = factory.LazyAttribute(lambda o: o.document.workspace)
    document_type = "invoice"
    status = ExtractionStatus.PENDING_REVIEW


class ExtractedFieldFactory(DjangoModelFactory):
    class Meta:
        model = ExtractedField

    extraction = factory.SubFactory(DocumentExtractionFactory)
    key = "total"
    label = "Total"
    display_value = "100.00"
    normalized_value = "100.00"
    confidence = 0.9
    is_required = True


class ConversationFactory(DjangoModelFactory):
    class Meta:
        model = Conversation

    workspace = factory.SubFactory(WorkspaceFactory)
    created_by = factory.SubFactory(UserFactory)


class DocumentChunkFactory(DjangoModelFactory):
    class Meta:
        model = DocumentChunk

    document = factory.SubFactory(DocumentFactory)
    workspace = factory.LazyAttribute(lambda o: o.document.workspace)
    chunk_index = factory.Sequence(lambda n: n)
    page_number = 1
    text = "Sample indexed text."
    embedding = factory.LazyFunction(lambda: [0.0] * 256)


class WorkflowFactory(DjangoModelFactory):
    class Meta:
        model = Workflow

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"Workflow {n}")
    created_by = factory.SubFactory(UserFactory)


class ApprovalRequestFactory(DjangoModelFactory):
    class Meta:
        model = ApprovalRequest

    workspace = factory.SubFactory(WorkspaceFactory)
    title = factory.Sequence(lambda n: f"Approval {n}")
    risk_level = "low"
    assigned_role = Role.ADMIN
    requested_by = factory.SubFactory(UserFactory)


class WebhookEndpointFactory(DjangoModelFactory):
    class Meta:
        model = WebhookEndpoint
        skip_postgeneration_save = True

    workspace = factory.SubFactory(WorkspaceFactory)
    name = factory.Sequence(lambda n: f"Endpoint {n}")
    url = "https://example.com/hooks/docpilot"
    is_active = True

    @factory.post_generation
    def secret(self, create, extracted, **kwargs):
        self.set_secret(extracted or "a-shared-webhook-secret")
        if create:
            self.save(update_fields=["encrypted_secret"])


class NotificationFactory(DjangoModelFactory):
    class Meta:
        model = Notification

    workspace = factory.SubFactory(WorkspaceFactory)
    user = factory.SubFactory(UserFactory)
    event_type = "approval.requested"
    title = factory.Sequence(lambda n: f"Notification {n}")
