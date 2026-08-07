import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.validation import validate_upload


def test_accepts_a_valid_pdf():
    file = SimpleUploadedFile("a.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")
    validate_upload(file)  # does not raise


def test_accepts_a_valid_png():
    file = SimpleUploadedFile("a.png", b"\x89PNG\r\n\x1a\nrest", content_type="image/png")
    validate_upload(file)


def test_accepts_csv_and_txt_without_a_signature_check():
    validate_upload(SimpleUploadedFile("a.csv", b"a,b,c", content_type="text/csv"))
    validate_upload(SimpleUploadedFile("a.txt", b"hello", content_type="text/plain"))


def test_rejects_a_disallowed_extension():
    file = SimpleUploadedFile("a.exe", b"MZ", content_type="application/octet-stream")
    with pytest.raises(ValidationError):
        validate_upload(file)


def test_rejects_a_declared_type_that_does_not_match_the_extension():
    file = SimpleUploadedFile("a.pdf", b"%PDF-1.4", content_type="image/png")
    with pytest.raises(ValidationError):
        validate_upload(file)


def test_allows_a_generic_octet_stream_declared_type_through_to_the_signature_check():
    file = SimpleUploadedFile("a.pdf", b"%PDF-1.4", content_type="application/octet-stream")
    validate_upload(file)  # does not raise — real PDF signature present


def test_rejects_content_that_does_not_match_its_signature():
    file = SimpleUploadedFile("a.pdf", b"not a pdf at all", content_type="application/pdf")
    with pytest.raises(ValidationError):
        validate_upload(file)


def test_rejects_a_file_over_the_configured_size_limit(settings):
    settings.DOCUMENT_MAX_UPLOAD_SIZE_BYTES = 4
    file = SimpleUploadedFile("a.pdf", b"%PDF-1.4", content_type="application/pdf")
    with pytest.raises(ValidationError):
        validate_upload(file)
