"""Unit tests for the pure stage functions in apps/processing/pipeline.py
— no database, no Celery, no real OCR. Each stage function takes a
(never-saved) ProcessingJob/Document pair and raw file bytes, and either
mutates the job's in-memory fields or raises a normalized
apps.processing.exceptions.ProcessingError subclass. See test_tasks.py
for the orchestrator that wires these together against a real DB.
"""

import pytest

from apps.documents.models import Document
from apps.extraction.models import DocumentExtraction
from apps.processing import pipeline
from apps.processing.exceptions import ValidationProcessingError
from apps.processing.models import ProcessingJob
from apps.processing.tests.fakes import FakeClassificationProvider, FakeOCRProvider
from apps.processing.tests.pdf_fixtures import (
    corrupt_pdf_bytes,
    digital_pdf_bytes,
    mixed_pdf_bytes,
    password_protected_pdf_bytes,
    scanned_pdf_bytes,
)
from tests.factories import ProcessingJobFactory


def _job(*, content_type: str = "application/pdf", filename: str = "invoice.pdf") -> ProcessingJob:
    document = Document(filename=filename, content_type=content_type, size_bytes=1)
    return ProcessingJob(document=document)


class TestStageValidate:
    def test_a_well_formed_digital_pdf_passes(self):
        pipeline.stage_validate(_job(), digital_pdf_bytes())  # must not raise

    def test_a_corrupt_pdf_is_rejected_with_a_normalized_code(self):
        with pytest.raises(ValidationProcessingError) as exc_info:
            pipeline.stage_validate(_job(), corrupt_pdf_bytes())
        assert exc_info.value.code == "corrupt_file"
        assert exc_info.value.retryable is False

    def test_a_password_protected_pdf_is_rejected_with_a_normalized_code(self):
        with pytest.raises(ValidationProcessingError) as exc_info:
            pipeline.stage_validate(_job(), password_protected_pdf_bytes())
        assert exc_info.value.code == "password_protected_pdf"
        assert exc_info.value.retryable is False

    def test_a_non_pdf_file_is_not_validated_as_a_pdf(self):
        # Images/docx/etc. have no pypdf-parseable structure to validate
        # here — Phase 3's upload-time validation already checked
        # extension/MIME/magic bytes; this stage only guards the PDF path.
        pipeline.stage_validate(
            _job(content_type="image/png"), b"not a pdf at all"
        )  # must not raise


class TestStageExtractText:
    def test_a_fully_digital_pdf_needs_no_ocr(self):
        job = _job()
        text, ocr_pages = pipeline.stage_extract_text(
            job, digital_pdf_bytes("Invoice total 500.00")
        )

        assert "Invoice total 500.00" in text
        assert ocr_pages == []
        assert job.total_pages == 1
        assert job.ocr_page_count == 0

    def test_a_fully_scanned_pdf_needs_ocr_on_its_only_page(self):
        job = _job()
        text, ocr_pages = pipeline.stage_extract_text(job, scanned_pdf_bytes())

        assert text == ""
        assert ocr_pages == [1]
        assert job.total_pages == 1
        assert job.ocr_page_count == 1

    def test_mixed_digital_and_scanned_pages_flags_only_the_scanned_one(self):
        job = _job()
        text, ocr_pages = pipeline.stage_extract_text(job, mixed_pdf_bytes())

        assert "Page one" in text
        assert "Page three" in text
        assert ocr_pages == [2]
        assert job.total_pages == 3
        assert job.ocr_page_count == 1

    def test_an_image_file_is_entirely_flagged_for_ocr(self):
        job = _job(content_type="image/png", filename="scan.png")
        text, ocr_pages = pipeline.stage_extract_text(job, b"\x89PNG fake bytes")

        assert text == ""
        assert ocr_pages == [1]
        assert job.total_pages == 1

    def test_an_unsupported_content_type_extracts_nothing_and_skips_ocr(self):
        job = _job(content_type="text/csv", filename="report.csv")
        text, ocr_pages = pipeline.stage_extract_text(job, b"a,b,c\n1,2,3")

        assert text == ""
        assert ocr_pages == []
        assert job.ocr_page_count == 0


class TestStageRunOcr:
    def test_skips_the_provider_entirely_when_no_pages_need_ocr(self):
        job = _job()
        provider = FakeOCRProvider()

        combined = pipeline.stage_run_ocr(job, digital_pdf_bytes("hello"), "hello", [], provider)

        assert combined == "hello"
        assert provider.page_calls == []

    def test_calls_the_provider_only_for_flagged_pages(self):
        job = _job()
        provider = FakeOCRProvider(text="scanned-text")

        combined = pipeline.stage_run_ocr(job, mixed_pdf_bytes(), "digital-text", [2], provider)

        assert provider.page_calls == [2]
        assert "digital-text" in combined
        assert "scanned-text" in combined

    def test_an_image_document_calls_extract_text_from_image_not_from_page(self):
        job = _job(content_type="image/png", filename="scan.png")
        provider = FakeOCRProvider(text="image-text")

        combined = pipeline.stage_run_ocr(job, b"fake-image-bytes", "", [1], provider)

        assert provider.image_calls == 1
        assert provider.page_calls == []
        assert "image-text" in combined


class TestStageClassify:
    def test_sets_document_type_from_the_provider_result(self):
        job = _job(filename="acme-invoice.pdf")
        provider = FakeClassificationProvider(result="invoice")

        pipeline.stage_classify(job, "some extracted text", provider)

        assert job.document_type == "invoice"
        assert provider.calls == [("acme-invoice.pdf", "some extracted text")]


@pytest.mark.django_db
class TestStageExtractFields:
    def test_non_invoice_documents_are_skipped_entirely(self):
        job = ProcessingJobFactory()
        job.document_type = "contract"

        pipeline.stage_extract_fields(job, "Vendor Name: Acme\nTotal: 1.00\n")

        assert not DocumentExtraction.objects.filter(document=job.document).exists()

    def test_an_extraction_service_failure_does_not_raise(self, monkeypatch):
        job = ProcessingJobFactory()
        job.document_type = "invoice"

        def _boom(*args, **kwargs):
            raise RuntimeError("provider exploded")

        monkeypatch.setattr("apps.extraction.services.build_extraction_for_job", _boom)

        pipeline.stage_extract_fields(job, "Total: 1.00")  # must not raise

    def test_an_invoice_document_creates_an_extraction(self):
        job = ProcessingJobFactory()
        job.document_type = "invoice"

        pipeline.stage_extract_fields(job, "Invoice Number: INV-1\nTotal: 10.00\n")

        assert DocumentExtraction.objects.filter(document=job.document).exists()


class TestBuildPageTexts:
    def test_returns_digital_text_per_page_for_a_fully_digital_pdf(self):
        job = _job()

        pages = pipeline.build_page_texts(job, digital_pdf_bytes(), [], FakeOCRProvider())

        assert [p for p, _ in pages] == list(range(1, len(pages) + 1))
        assert all(text for _, text in pages)

    def test_ocrs_only_the_flagged_pages(self):
        job = _job()
        provider = FakeOCRProvider(text="scanned-text")

        pages = pipeline.build_page_texts(job, mixed_pdf_bytes(), [2], provider)

        assert provider.page_calls == [2]
        page_2_text = next(text for p, text in pages if p == 2)
        assert "scanned-text" in page_2_text

    def test_an_image_document_uses_the_image_ocr_path(self):
        job = _job(content_type="image/png", filename="scan.png")
        provider = FakeOCRProvider(text="image-text")

        pages = pipeline.build_page_texts(job, b"fake-image-bytes", [1], provider)

        assert pages == [(1, "image-text")]

    def test_pages_with_no_text_at_all_are_omitted(self):
        job = _job(content_type="text/plain", filename="empty.txt")

        pages = pipeline.build_page_texts(job, b"", [], FakeOCRProvider())

        assert pages == []


@pytest.mark.django_db
class TestStageIndex:
    def test_creates_chunks_for_the_document(self):
        from apps.assistant.models import DocumentChunk
        from tests.factories import ProcessingJobFactory

        job = ProcessingJobFactory()

        chunk_count = pipeline.stage_index(job, [(1, "Some indexable text about a contract.")])

        assert chunk_count == 1
        assert DocumentChunk.objects.filter(document=job.document).count() == 1

    def test_an_indexing_failure_does_not_raise(self, monkeypatch):
        from tests.factories import ProcessingJobFactory

        job = ProcessingJobFactory()

        def _boom(*args, **kwargs):
            raise RuntimeError("embedding provider exploded")

        monkeypatch.setattr("apps.assistant.services.index_document", _boom)

        chunk_count = pipeline.stage_index(job, [(1, "text")])  # must not raise

        assert chunk_count == 0
