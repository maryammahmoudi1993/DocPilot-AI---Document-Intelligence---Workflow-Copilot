"""Unit tests for S3StorageBackend against a mocked boto3 client — no
network call to real S3/MinIO (project rule: mock external providers at
module boundaries). These verify DocPilot's own code calls boto3
correctly, not boto3/S3's behavior itself.
"""

from io import BytesIO
from unittest.mock import MagicMock, patch

from apps.documents.storage import S3StorageBackend


def test_upload_calls_boto3_upload_fileobj_with_the_bucket_key_and_content_type(settings):
    settings.DOCUMENT_STORAGE_BUCKET = "test-bucket"
    client = MagicMock()
    backend = S3StorageBackend(client=client)
    fileobj = BytesIO(b"content")

    backend.upload(key="ws/doc.pdf", fileobj=fileobj, content_type="application/pdf")

    client.upload_fileobj.assert_called_once_with(
        fileobj, "test-bucket", "ws/doc.pdf", ExtraArgs={"ContentType": "application/pdf"}
    )


def test_generate_presigned_url_passes_the_key_bucket_and_expiry_through(settings):
    # The backend never reads DOCUMENT_SIGNED_URL_EXPIRY_SECONDS itself —
    # the caller (services.get_document_signed_url) decides the expiry
    # and passes it explicitly, keeping this backend Django-settings-
    # agnostic.
    settings.DOCUMENT_STORAGE_BUCKET = "test-bucket"
    client = MagicMock()
    client.generate_presigned_url.return_value = "https://example.test/signed"
    backend = S3StorageBackend(client=client)

    url = backend.generate_presigned_url(key="ws/doc.pdf", expires_in=300)

    assert url == "https://example.test/signed"
    client.generate_presigned_url.assert_called_once_with(
        "get_object", Params={"Bucket": "test-bucket", "Key": "ws/doc.pdf"}, ExpiresIn=300
    )


def test_presigned_urls_use_the_client_by_default_when_no_public_endpoint_is_configured(settings):
    settings.DOCUMENT_STORAGE_PUBLIC_ENDPOINT_URL = ""
    client = MagicMock()
    backend = S3StorageBackend(client=client)

    backend.generate_presigned_url(key="ws/doc.pdf", expires_in=60)

    client.generate_presigned_url.assert_called_once()


def test_presigned_urls_use_a_separate_client_when_a_public_endpoint_is_configured(settings):
    """The internal client (talks to the Docker-network hostname) and
    the presign client (must build a URL the browser can reach) are
    deliberately different objects when the endpoints differ — see the
    module docstring."""
    settings.DOCUMENT_STORAGE_ENDPOINT_URL = "http://minio:9000"
    settings.DOCUMENT_STORAGE_PUBLIC_ENDPOINT_URL = "http://localhost:9000"
    internal_client = MagicMock()
    public_client = MagicMock()

    with patch(
        "apps.documents.storage.boto3.client", side_effect=[internal_client, public_client]
    ) as mocked:
        backend = S3StorageBackend()

    assert mocked.call_args_list[0].kwargs["endpoint_url"] == "http://minio:9000"
    assert mocked.call_args_list[1].kwargs["endpoint_url"] == "http://localhost:9000"

    backend.generate_presigned_url(key="ws/doc.pdf", expires_in=60)
    public_client.generate_presigned_url.assert_called_once()
    internal_client.generate_presigned_url.assert_not_called()

    backend.upload(key="ws/doc.pdf", fileobj=BytesIO(b"x"), content_type="application/pdf")
    internal_client.upload_fileobj.assert_called_once()


def test_delete_calls_boto3_delete_object_with_the_bucket_and_key(settings):
    settings.DOCUMENT_STORAGE_BUCKET = "test-bucket"
    client = MagicMock()
    backend = S3StorageBackend(client=client)

    backend.delete(key="ws/doc.pdf")

    client.delete_object.assert_called_once_with(Bucket="test-bucket", Key="ws/doc.pdf")
