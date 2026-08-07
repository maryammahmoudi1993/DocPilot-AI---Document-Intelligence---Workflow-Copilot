import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import User
from apps.documents.models import Document
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
