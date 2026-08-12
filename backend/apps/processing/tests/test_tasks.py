"""Integration tests for the pipeline orchestrator task
(apps/processing/tasks.run_processing_pipeline) against a real (sqlite,
per test settings) database. CELERY_TASK_ALWAYS_EAGER=True (test
settings) makes `.delay(...)` run synchronously in-process — no broker,
no worker, and (via the fake OCR/classification providers below) no
real OCR/LLM call, per the project rule against paid providers in unit
tests.
"""

import pytest

from apps.processing.exceptions import RetryableProcessingError
from apps.processing.models import ProcessingStage
from apps.processing.tasks import MAX_ATTEMPTS, run_processing_pipeline
from apps.processing.tests.fakes import FakeClassificationProvider, FakeOCRProvider
from apps.processing.tests.pdf_fixtures import (
    corrupt_pdf_bytes,
    digital_pdf_bytes,
    mixed_pdf_bytes,
    password_protected_pdf_bytes,
    scanned_pdf_bytes,
)
from tests.factories import DocumentFactory, ProcessingJobFactory


@pytest.fixture
def fake_providers(monkeypatch):
    """Patches the module-qualified provider lookups tasks.py uses (see
    apps/processing/providers.py) so no test ever touches tesseract,
    pdf2image, or a real classifier — matches the project rule to mock
    external providers at module boundaries."""
    ocr = FakeOCRProvider()
    classification = FakeClassificationProvider(result="invoice")
    monkeypatch.setattr("apps.processing.tasks.get_ocr_provider", lambda: ocr)
    monkeypatch.setattr("apps.processing.tasks.get_classification_provider", lambda: classification)
    return ocr, classification


def _job_with_file(fake_storage, *, content_type="application/pdf", pdf_bytes=None):
    document = DocumentFactory(content_type=content_type)
    fake_storage.objects[document.storage_key] = (
        pdf_bytes if pdf_bytes is not None else digital_pdf_bytes()
    )
    return ProcessingJobFactory(document=document, workspace=document.workspace)


@pytest.mark.django_db
class TestSuccessfulPaths:
    def test_a_fully_digital_pdf_completes_without_calling_ocr(self, fake_storage, fake_providers):
        ocr, classification = fake_providers
        job = _job_with_file(
            fake_storage, pdf_bytes=digital_pdf_bytes("Total amount due: 900.00 USD")
        )

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert job.stage == ProcessingStage.COMPLETED
        assert job.ocr_page_count == 0
        assert ocr.page_calls == []
        assert classification.calls  # classification still runs
        assert job.document_type == "invoice"
        assert job.completed_at is not None

    def test_a_scanned_pdf_completes_and_calls_ocr_for_its_page(self, fake_storage, fake_providers):
        ocr, _ = fake_providers
        job = _job_with_file(fake_storage, pdf_bytes=scanned_pdf_bytes())

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert job.stage == ProcessingStage.COMPLETED
        assert job.ocr_page_count == 1
        assert ocr.page_calls == [1]

    def test_mixed_digital_and_scanned_pages_only_ocrs_the_scanned_one(
        self, fake_storage, fake_providers
    ):
        ocr, _ = fake_providers
        job = _job_with_file(fake_storage, pdf_bytes=mixed_pdf_bytes())

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert job.stage == ProcessingStage.COMPLETED
        assert job.total_pages == 3
        assert ocr.page_calls == [2]

    def test_every_stage_completes_as_real_work_not_a_placeholder(
        self, fake_storage, fake_providers
    ):
        """As of Phase 6, no stage in STAGE_ORDER is a deferred
        placeholder any more — extracting_fields/validating_extraction/
        scoring_confidence (Phase 5) and indexing (Phase 6) all record
        real completions, never a fabricated or skipped result."""
        job = _job_with_file(fake_storage)

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        by_stage = {
            entry["stage"]: entry for entry in job.stage_history if entry["status"] != "started"
        }
        for stage in (
            ProcessingStage.EXTRACTING_FIELDS,
            ProcessingStage.VALIDATING_EXTRACTION,
            ProcessingStage.SCORING_CONFIDENCE,
            ProcessingStage.INDEXING,
        ):
            assert by_stage[stage]["status"] == "completed"


@pytest.mark.django_db
class TestValidationFailures:
    def test_a_corrupt_file_fails_immediately_without_retrying(self, fake_storage, fake_providers):
        job = _job_with_file(fake_storage, pdf_bytes=corrupt_pdf_bytes())

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert job.stage == ProcessingStage.FAILED
        assert job.error_code == "corrupt_file"
        assert job.is_retryable is False
        assert job.attempt_count == 1

    def test_a_password_protected_pdf_fails_immediately_without_retrying(
        self, fake_storage, fake_providers
    ):
        job = _job_with_file(fake_storage, pdf_bytes=password_protected_pdf_bytes())

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert job.stage == ProcessingStage.FAILED
        assert job.error_code == "password_protected_pdf"
        assert job.is_retryable is False
        assert job.attempt_count == 1

    def test_error_codes_are_stable_short_slugs_not_raw_exception_text(
        self, fake_storage, fake_providers
    ):
        job = _job_with_file(fake_storage, pdf_bytes=corrupt_pdf_bytes())

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert job.error_code is not None
        assert " " not in job.error_code
        assert "Traceback" not in (job.error_message or "")


@pytest.mark.django_db
class TestRetryBehavior:
    def test_a_retryable_provider_failure_retries_and_then_succeeds(
        self, fake_storage, monkeypatch
    ):
        ocr = FakeOCRProvider(
            fail_times=1,
            error=RetryableProcessingError("OCR provider timed out.", code="ocr_provider_timeout"),
        )
        classification = FakeClassificationProvider(result="invoice")
        monkeypatch.setattr("apps.processing.tasks.get_ocr_provider", lambda: ocr)
        monkeypatch.setattr(
            "apps.processing.tasks.get_classification_provider", lambda: classification
        )
        job = _job_with_file(fake_storage, pdf_bytes=scanned_pdf_bytes())

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert job.stage == ProcessingStage.COMPLETED
        assert job.attempt_count == 2  # first attempt failed, second succeeded

    def test_a_persistently_retryable_failure_eventually_fails_as_retryable(
        self, fake_storage, monkeypatch
    ):
        ocr = FakeOCRProvider(
            fail_times=99,
            error=RetryableProcessingError(
                "OCR provider unavailable.", code="ocr_provider_unavailable"
            ),
        )
        monkeypatch.setattr("apps.processing.tasks.get_ocr_provider", lambda: ocr)
        monkeypatch.setattr(
            "apps.processing.tasks.get_classification_provider",
            lambda: FakeClassificationProvider(),
        )
        job = _job_with_file(fake_storage, pdf_bytes=scanned_pdf_bytes())

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert job.stage == ProcessingStage.FAILED
        assert job.is_retryable is True
        assert job.error_code == "ocr_provider_unavailable"
        assert job.attempt_count == MAX_ATTEMPTS


@pytest.mark.django_db
class TestIdempotency:
    def test_running_an_already_completed_job_again_is_a_safe_no_op(
        self, fake_storage, fake_providers
    ):
        ocr, _ = fake_providers
        job = _job_with_file(fake_storage)
        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()
        history_length_after_first_run = len(job.stage_history)

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert job.stage == ProcessingStage.COMPLETED
        assert len(job.stage_history) == history_length_after_first_run
        assert ocr.page_calls == []  # never called again either

    def test_a_missing_job_id_is_a_safe_no_op_not_a_crash(self, fake_storage, fake_providers):
        run_processing_pipeline.delay("00000000-0000-0000-0000-000000000000")  # must not raise


@pytest.mark.django_db
class TestSafeRawResultPersistence:
    def test_raw_text_excerpt_is_bounded_even_for_very_long_ocr_output(
        self, fake_storage, monkeypatch
    ):
        very_long_text = "x" * 5000
        ocr = FakeOCRProvider(text=very_long_text)
        monkeypatch.setattr("apps.processing.tasks.get_ocr_provider", lambda: ocr)
        monkeypatch.setattr(
            "apps.processing.tasks.get_classification_provider",
            lambda: FakeClassificationProvider(),
        )
        job = _job_with_file(fake_storage, pdf_bytes=scanned_pdf_bytes())

        run_processing_pipeline.delay(str(job.id))
        job.refresh_from_db()

        assert len(job.raw_text_excerpt) <= 2000
