from datetime import timedelta

import pytest
from django.utils import timezone

from apps.approvals import services
from apps.approvals.exceptions import InvalidApprovalTransitionError
from apps.approvals.models import ApprovalRequest, ApprovalStatus
from apps.notifications.models import Notification
from tests.factories import ApprovalRequestFactory, UserFactory, WorkspaceFactory


@pytest.mark.django_db
class TestCreateApprovalRequest:
    def test_creates_a_pending_request_and_notifies_the_assigned_role(self):
        from apps.workspaces.models import Role
        from tests.factories import WorkspaceMembershipFactory

        workspace = WorkspaceFactory()
        approver = UserFactory()
        WorkspaceMembershipFactory(user=approver, workspace=workspace, role=Role.ADMIN)
        requester = UserFactory()

        approval = services.create_approval_request(
            workspace=workspace,
            title="Invoice over threshold",
            risk_level="high",
            assigned_role=Role.ADMIN,
            requested_by=requester,
        )

        assert approval.status == ApprovalStatus.PENDING
        assert approval.risk_level == "high"
        assert Notification.objects.filter(user=approver, event_type="approval.requested").exists()

    def test_resolves_document_id_to_a_real_document(self):
        from tests.factories import DocumentFactory

        workspace = WorkspaceFactory()
        document = DocumentFactory(workspace=workspace)

        approval = services.create_approval_request(
            workspace=workspace, title="Review", document_id=str(document.id)
        )

        assert approval.document_id == document.id


@pytest.mark.django_db
class TestDecide:
    def test_approving_a_pending_request_records_decision_and_notifies_requester(self):
        requester = UserFactory()
        approver = UserFactory()
        approval = ApprovalRequestFactory(requested_by=requester)

        decided = services.decide(approval=approval, new_status="approved", user=approver)

        assert decided.status == "approved"
        assert decided.decided_by_id == approver.id
        assert decided.decided_at is not None
        assert Notification.objects.filter(user=requester, event_type="approval.approved").exists()

    def test_rejecting_records_an_optional_reason_as_a_comment(self):
        approval = ApprovalRequestFactory()
        approver = UserFactory()

        services.decide(approval=approval, new_status="rejected", user=approver, reason="Too risky")

        assert approval.comments.filter(body="Too risky", author=approver).exists()

    def test_repeating_the_same_decision_is_a_safe_no_op(self):
        approval = ApprovalRequestFactory()
        approver = UserFactory()
        services.decide(approval=approval, new_status="approved", user=approver)
        notifications_before = Notification.objects.count()

        result = services.decide(approval=approval, new_status="approved", user=approver)

        assert result.status == "approved"
        assert Notification.objects.count() == notifications_before

    def test_deciding_differently_after_a_decision_is_rejected(self):
        approval = ApprovalRequestFactory()
        approver = UserFactory()
        services.decide(approval=approval, new_status="approved", user=approver)

        with pytest.raises(InvalidApprovalTransitionError):
            services.decide(approval=approval, new_status="rejected", user=approver)

    def test_an_expired_request_cannot_be_approved(self):
        approval = ApprovalRequestFactory(expires_at=timezone.now() - timedelta(minutes=1))
        approver = UserFactory()

        with pytest.raises(InvalidApprovalTransitionError):
            services.decide(approval=approval, new_status="approved", user=approver)

        # decide() is wrapped in @transaction.atomic, so the lazy-expiry
        # write it made along the way is rolled back with everything else
        # once it raises — the request is still pending in the database,
        # not silently left half-transitioned.
        approval.refresh_from_db()
        assert approval.status == ApprovalStatus.PENDING

    def test_expiring_twice_is_a_safe_no_op_not_an_error(self):
        approval = ApprovalRequestFactory(expires_at=timezone.now() - timedelta(minutes=1))

        with pytest.raises(InvalidApprovalTransitionError):
            services.decide(approval=approval, new_status="approved", user=UserFactory())

        result = services.decide(approval=approval, new_status="expired", user=UserFactory())
        assert result.status == ApprovalStatus.EXPIRED


@pytest.mark.django_db
def test_add_comment_persists_and_records_an_audit_event():
    from apps.audit.models import AuditEvent

    approval = ApprovalRequestFactory()
    author = UserFactory()

    comment = services.add_comment(approval=approval, author=author, body="Looks fine to me.")

    assert comment.body == "Looks fine to me."
    assert AuditEvent.objects.filter(event_type="approval.commented").exists()


@pytest.mark.django_db
def test_is_expired_property_only_true_while_pending_and_past_expiry():
    approval = ApprovalRequestFactory(expires_at=timezone.now() - timedelta(minutes=1))
    assert approval.is_expired is True

    approval.status = ApprovalStatus.APPROVED
    assert approval.is_expired is False


@pytest.mark.django_db
def test_workspace_scoped_creation_is_isolated_from_other_workspaces():
    workspace_a = WorkspaceFactory()
    workspace_b = WorkspaceFactory()
    services.create_approval_request(workspace=workspace_a, title="A's approval")

    assert ApprovalRequest.objects.filter(workspace=workspace_a).count() == 1
    assert ApprovalRequest.objects.filter(workspace=workspace_b).count() == 0
