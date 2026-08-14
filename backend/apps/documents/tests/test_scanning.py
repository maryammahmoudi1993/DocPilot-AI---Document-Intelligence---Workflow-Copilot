"""Malware-scanning integration interface (Phase 10 gap: 'Add malware-
scanning integration interface without requiring a paid service in
tests'). No paid/network AV provider is called here or anywhere in the
default configuration — the default provider is a deterministic,
offline signature check for the industry-standard EICAR antivirus test
string, the same technique real AV test suites use to verify a scanning
path works without needing an actual virus sample."""

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.documents.scanning import (
    EICAR_SIGNATURE,
    EicarSignatureScanProvider,
    MalwareScanResult,
    NullMalwareScanProvider,
    get_malware_scan_provider,
)


class TestEicarSignatureScanProvider:
    def test_reports_clean_for_ordinary_content(self):
        provider = EicarSignatureScanProvider()
        file = SimpleUploadedFile(
            "a.pdf", b"%PDF-1.4\nordinary content", content_type="application/pdf"
        )

        result = provider.scan(fileobj=file)

        assert isinstance(result, MalwareScanResult)
        assert result.is_clean is True
        assert result.threat_name is None
        assert result.provider == "eicar-signature"

    def test_flags_the_eicar_test_signature(self):
        provider = EicarSignatureScanProvider()
        file = SimpleUploadedFile("a.txt", EICAR_SIGNATURE, content_type="text/plain")

        result = provider.scan(fileobj=file)

        assert result.is_clean is False
        assert result.threat_name == "EICAR-Test-Signature"

    def test_flags_the_signature_even_when_not_at_the_start_of_the_file(self):
        provider = EicarSignatureScanProvider()
        file = SimpleUploadedFile(
            "a.txt",
            b"leading bytes " + EICAR_SIGNATURE + b" trailing bytes",
            content_type="text/plain",
        )

        result = provider.scan(fileobj=file)

        assert result.is_clean is False

    def test_does_not_consume_the_file_pointer(self):
        """The pipeline reads the same fileobj again after scanning
        (checksum, storage upload) — scanning must leave the read
        position exactly where it found it."""
        provider = EicarSignatureScanProvider()
        file = SimpleUploadedFile("a.pdf", b"%PDF-1.4\ncontent", content_type="application/pdf")
        file.seek(3)

        provider.scan(fileobj=file)

        assert file.tell() == 3


class TestNullMalwareScanProvider:
    def test_always_reports_clean(self):
        provider = NullMalwareScanProvider()
        file = SimpleUploadedFile("a.txt", EICAR_SIGNATURE, content_type="text/plain")

        result = provider.scan(fileobj=file)

        assert result.is_clean is True
        assert result.provider == "null"


class TestGetMalwareScanProvider:
    def test_defaults_to_the_eicar_signature_provider(self, settings):
        settings.DOCUMENT_MALWARE_SCAN_PROVIDER = "eicar"
        assert isinstance(get_malware_scan_provider(), EicarSignatureScanProvider)

    def test_null_provider_is_selectable_by_setting(self, settings):
        settings.DOCUMENT_MALWARE_SCAN_PROVIDER = "null"
        assert isinstance(get_malware_scan_provider(), NullMalwareScanProvider)

    def test_unknown_provider_name_falls_back_to_eicar(self, settings):
        settings.DOCUMENT_MALWARE_SCAN_PROVIDER = "not-a-real-provider"
        assert isinstance(get_malware_scan_provider(), EicarSignatureScanProvider)


@pytest.mark.django_db
class TestCreateDocumentRejectsFlaggedUploads:
    """Integration point: apps/documents/services.py:create_document
    must reject a flagged upload before it ever reaches storage."""

    def test_upload_containing_the_eicar_signature_is_rejected(self):
        from apps.documents.services import create_document
        from apps.documents.tests.fakes import FakeStorageBackend
        from tests.factories import UserFactory, WorkspaceFactory

        workspace = WorkspaceFactory()
        user = UserFactory()
        file = SimpleUploadedFile("eicar.txt", EICAR_SIGNATURE, content_type="text/plain")
        storage = FakeStorageBackend()

        with pytest.raises(ValidationError):
            create_document(
                workspace=workspace, uploaded_by=user, uploaded_file=file, storage=storage
            )

        assert storage.objects == {}
