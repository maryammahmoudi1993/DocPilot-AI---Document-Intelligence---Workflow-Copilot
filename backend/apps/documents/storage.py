"""Object storage abstraction.

One interface (`StorageBackend`), one concrete implementation
(`S3StorageBackend`, boto3 against any S3-compatible endpoint — MinIO
locally, real S3 in deployment — see docker-compose.yml and
config/settings/base.py's DOCUMENT_STORAGE_* settings). Everything else
in this app (services.py) depends only on the interface, so it's
testable without a network call to real storage (see
apps/documents/tests/test_storage.py, which mocks the boto3 client
directly — the project rule to mock external providers at module
boundaries).

Files are never public. The only way to read one back is a short-lived
signed URL generated per request (see DOCUMENT_SIGNED_URL_EXPIRY_SECONDS)
— nothing persists or caches that URL beyond the response it's returned in.

Two endpoints, on purpose: uploads/deletes go over
DOCUMENT_STORAGE_ENDPOINT_URL (the backend container's route to MinIO —
the internal Docker network hostname, e.g. http://minio:9000), but a
presigned URL has to be *reachable by the browser*, which can't resolve
that internal hostname at all — it only has the host-mapped port (e.g.
http://localhost:9000). Signing with the wrong endpoint produces a URL
that 404s/refuses to connect for the user, silently. See
DOCUMENT_STORAGE_PUBLIC_ENDPOINT_URL and docs/adr/0004-storage-abstraction.md.
"""

from typing import BinaryIO, Protocol

import boto3
from botocore.client import Config
from django.conf import settings


class StorageBackend(Protocol):
    def upload(self, *, key: str, fileobj: BinaryIO, content_type: str) -> None: ...

    def generate_presigned_url(self, *, key: str, expires_in: int) -> str: ...

    def delete(self, *, key: str) -> None: ...


class S3StorageBackend:
    def __init__(self, *, client=None, presign_client=None) -> None:
        self._client = (
            client
            if client is not None
            else self._build_client(settings.DOCUMENT_STORAGE_ENDPOINT_URL)
        )
        if presign_client is not None:
            self._presign_client = presign_client
        elif settings.DOCUMENT_STORAGE_PUBLIC_ENDPOINT_URL:
            self._presign_client = self._build_client(settings.DOCUMENT_STORAGE_PUBLIC_ENDPOINT_URL)
        else:
            # No separate public endpoint configured (e.g. running the
            # backend natively, outside Docker, where there's only ever
            # one reachable endpoint) — reuse the same client.
            self._presign_client = self._client
        self._bucket = settings.DOCUMENT_STORAGE_BUCKET

    @staticmethod
    def _build_client(endpoint_url: str):
        addressing_style = "path" if settings.DOCUMENT_STORAGE_USE_PATH_STYLE else "auto"
        return boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=settings.DOCUMENT_STORAGE_ACCESS_KEY,
            aws_secret_access_key=settings.DOCUMENT_STORAGE_SECRET_KEY,
            region_name=settings.DOCUMENT_STORAGE_REGION,
            config=Config(signature_version="s3v4", s3={"addressing_style": addressing_style}),
        )

    def upload(self, *, key: str, fileobj: BinaryIO, content_type: str) -> None:
        self._client.upload_fileobj(
            fileobj, self._bucket, key, ExtraArgs={"ContentType": content_type}
        )

    def generate_presigned_url(self, *, key: str, expires_in: int) -> str:
        return self._presign_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )

    def delete(self, *, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


_default_backend: StorageBackend | None = None


def get_storage_backend() -> StorageBackend:
    """Lazily-constructed process-wide default — lazy so importing this
    module never requires storage credentials/settings to be valid (only
    constructing a backend does)."""
    global _default_backend
    if _default_backend is None:
        _default_backend = S3StorageBackend()
    return _default_backend
