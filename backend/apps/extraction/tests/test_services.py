"""Service-layer tests for extraction, business validation, correction,
and review transitions — no HTTP involved (see test_views.py for the API
contract). Uses the deterministic RegexInvoiceExtractionProvider so
these are the project's "deterministic mocked test set" for extraction."""

import pytest

from apps.extraction import services
from apps.extraction.exceptions import (
    ExtractionLockedError,
    InvalidTransitionError,
    StaleVersionError,
)
from apps.extraction.models import ExtractionStatus, ValidationSeverity
from apps.extraction.providers import RegexInvoiceExtractionProvider
from apps.processing.models import DocumentType
from tests.factories import (
    DocumentExtractionFactory,
    DocumentFactory,
    ExtractedFieldFactory,
    ProcessingJobFactory,
    UserFactory,
)

VALID_INVOICE_TEXT = """
Vendor Name: Acme Supplies
Invoice Number: INV-1001
Invoice Date: 2026-01-01
Due Date: 2026-02-01
Subtotal: 100.00
Tax: 10.00
Discount: 0.00
Total: 110.00
"""


@pytest.mark.django_db
class TestBuildExtractionForJob:
    def test_extracts_all_schema_fields_from_matching_text(self):
        document = DocumentFactory()
        job = ProcessingJobFactory(document=document, workspace=document.workspace)
        job.document_type = DocumentType.INVOICE

        extraction = services.build_extraction_for_job(
            job, text=VALID_INVOICE_TEXT, provider=RegexInvoiceExtractionProvider()
        )

        assert extraction is not None
        assert extraction.status == ExtractionStatus.PENDING_REVIEW
        field_values = {f.key: f.normalized_value for f in extraction.fields.all()}
        assert field_values["invoice_number"] == "INV-1001"
        assert field_values["total"] == "110.00"
        assert extraction.overall_confidence == pytest.approx(0.92)

    def test_no_business_validation_issues_for_a_clean_invoice(self):
        document = DocumentFactory()
        job = ProcessingJobFactory(document=document, workspace=document.workspace)
        job.document_type = DocumentType.INVOICE

        extraction = services.build_extraction_for_job(
            job, text=VALID_INVOICE_TEXT, provider=RegexInvoiceExtractionProvider()
        )

        assert extraction.issues.filter(severity=ValidationSeverity.ERROR).count() == 0

    def test_missing_required_field_creates_a_review_issue(self):
        document = DocumentFactory()
        job = ProcessingJobFactory(document=document, workspace=document.workspace)
        job.document_type = DocumentType.INVOICE
        text_without_total = VALID_INVOICE_TEXT.replace("Total: 110.00", "")

        extraction = services.build_extraction_for_job(
            job, text=text_without_total, provider=RegexInvoiceExtractionProvider()
        )

        codes = {issue.code for issue in extraction.issues.all()}
        assert "required_field_missing" in codes

    def test_arithmetic_mismatch_is_flagged(self):
        document = DocumentFactory()
        job = ProcessingJobFactory(document=document, workspace=document.workspace)
        job.document_type = DocumentType.INVOICE
        bad_text = VALID_INVOICE_TEXT.replace("Total: 110.00", "Total: 999.00")

        extraction = services.build_extraction_for_job(
            job, text=bad_text, provider=RegexInvoiceExtractionProvider()
        )

        codes = {issue.code for issue in extraction.issues.all()}
        assert "arithmetic_mismatch" in codes

    def test_due_date_before_invoice_date_is_flagged(self):
        document = DocumentFactory()
        job = ProcessingJobFactory(document=document, workspace=document.workspace)
        job.document_type = DocumentType.INVOICE
        bad_text = VALID_INVOICE_TEXT.replace("Due Date: 2026-02-01", "Due Date: 2025-12-01")

        extraction = services.build_extraction_for_job(
            job, text=bad_text, provider=RegexInvoiceExtractionProvider()
        )

        codes = {issue.code for issue in extraction.issues.all()}
        assert "due_date_before_invoice_date" in codes

    def test_is_idempotent_once_a_reviewer_has_corrected_a_field(self):
        document = DocumentFactory()
        job = ProcessingJobFactory(document=document, workspace=document.workspace)
        job.document_type = DocumentType.INVOICE

        extraction = services.build_extraction_for_job(
            job, text=VALID_INVOICE_TEXT, provider=RegexInvoiceExtractionProvider()
        )
        user = UserFactory()
        field = extraction.fields.get(key="total")
        services.correct_field(
            field=field, user=user, value="500.00", reason="fix", expected_version=1
        )

        # Re-running extraction (as a duplicate/retried task would) must
        # not clobber the reviewer's correction.
        services.build_extraction_for_job(
            job, text=VALID_INVOICE_TEXT, provider=RegexInvoiceExtractionProvider()
        )
        field.refresh_from_db()
        assert field.display_value == "500.00"

    def test_is_idempotent_once_approved(self):
        document = DocumentFactory()
        job = ProcessingJobFactory(document=document, workspace=document.workspace)
        job.document_type = DocumentType.INVOICE
        extraction = services.build_extraction_for_job(
            job, text=VALID_INVOICE_TEXT, provider=RegexInvoiceExtractionProvider()
        )
        user = UserFactory()
        services.transition_status(
            extraction=extraction,
            new_status=ExtractionStatus.APPROVED,
            user=user,
            expected_version=1,
        )

        services.build_extraction_for_job(
            job, text="Total: 1.00", provider=RegexInvoiceExtractionProvider()
        )
        extraction.refresh_from_db()
        assert extraction.status == ExtractionStatus.APPROVED
        assert extraction.fields.get(key="total").normalized_value == "110.00"


@pytest.mark.django_db
class TestCorrectField:
    def test_writes_before_and_after_values(self):
        extraction = DocumentExtractionFactory()
        field = ExtractedFieldFactory(extraction=extraction, key="total", display_value="100.00")
        user = UserFactory()

        services.correct_field(
            field=field, user=user, value="150.00", reason="typo", expected_version=1
        )

        correction = field.corrections.get()
        assert correction.before_value == "100.00"
        assert correction.after_value == "150.00"
        assert correction.corrected_by == user

    def test_bumps_extraction_version(self):
        extraction = DocumentExtractionFactory()
        field = ExtractedFieldFactory(extraction=extraction)
        user = UserFactory()

        services.correct_field(field=field, user=user, value="1", reason="", expected_version=1)

        extraction.refresh_from_db()
        assert extraction.version == 2

    def test_stale_version_is_rejected(self):
        extraction = DocumentExtractionFactory()
        field = ExtractedFieldFactory(extraction=extraction)
        user = UserFactory()

        with pytest.raises(StaleVersionError):
            services.correct_field(
                field=field, user=user, value="1", reason="", expected_version=99
            )

    def test_two_reviewers_cannot_silently_overwrite_one_another(self):
        extraction = DocumentExtractionFactory()
        field = ExtractedFieldFactory(extraction=extraction)
        reviewer_a, reviewer_b = UserFactory(), UserFactory()

        services.correct_field(
            field=field, user=reviewer_a, value="200.00", reason="", expected_version=1
        )
        # reviewer_b read version 1 before reviewer_a's write landed.
        with pytest.raises(StaleVersionError):
            services.correct_field(
                field=field, user=reviewer_b, value="300.00", reason="", expected_version=1
            )

        field.refresh_from_db()
        assert field.display_value == "200.00"

    def test_cannot_correct_an_approved_extraction(self):
        extraction = DocumentExtractionFactory(status=ExtractionStatus.APPROVED)
        field = ExtractedFieldFactory(extraction=extraction)
        user = UserFactory()

        with pytest.raises(ExtractionLockedError):
            services.correct_field(field=field, user=user, value="1", reason="", expected_version=1)


@pytest.mark.django_db
class TestTransitionStatus:
    def test_pending_review_can_be_approved_with_no_blocking_issues(self):
        extraction = DocumentExtractionFactory()
        user = UserFactory()

        result = services.transition_status(
            extraction=extraction,
            new_status=ExtractionStatus.APPROVED,
            user=user,
            expected_version=1,
        )

        assert result.status == ExtractionStatus.APPROVED
        assert result.approved_by == user

    def test_approval_blocked_by_unresolved_errors(self):
        extraction = DocumentExtractionFactory()
        field = ExtractedFieldFactory(extraction=extraction, is_required=True, normalized_value="")
        services.run_validations(extraction)
        assert extraction.issues.filter(severity=ValidationSeverity.ERROR).exists()
        user = UserFactory()

        with pytest.raises(InvalidTransitionError):
            services.transition_status(
                extraction=extraction,
                new_status=ExtractionStatus.APPROVED,
                user=user,
                expected_version=1,
            )
        del field  # unused beyond triggering the validation issue above

    def test_approved_is_a_terminal_state(self):
        extraction = DocumentExtractionFactory(status=ExtractionStatus.APPROVED, version=2)
        user = UserFactory()

        with pytest.raises(InvalidTransitionError):
            services.transition_status(
                extraction=extraction,
                new_status=ExtractionStatus.REJECTED,
                user=user,
                expected_version=2,
            )

    def test_rejected_can_return_to_pending_review(self):
        extraction = DocumentExtractionFactory(status=ExtractionStatus.REJECTED, version=2)
        user = UserFactory()

        result = services.transition_status(
            extraction=extraction,
            new_status=ExtractionStatus.PENDING_REVIEW,
            user=user,
            expected_version=2,
        )

        assert result.status == ExtractionStatus.PENDING_REVIEW

    def test_stale_version_on_transition_is_rejected(self):
        extraction = DocumentExtractionFactory()
        user = UserFactory()

        with pytest.raises(StaleVersionError):
            services.transition_status(
                extraction=extraction,
                new_status=ExtractionStatus.APPROVED,
                user=user,
                expected_version=5,
            )


@pytest.mark.django_db
def test_normalize_value_strips_currency_formatting():
    assert services.normalize_value("total", "$1,200.50") == "1200.50"


@pytest.mark.django_db
def test_normalize_value_rejects_unparseable_date():
    assert services.normalize_value("invoice_date", "not a date") is None
