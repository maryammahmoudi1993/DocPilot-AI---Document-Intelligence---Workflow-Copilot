"""In-memory fake of the StorageBackend protocol — no network call to
real S3/MinIO (project rule: mock external providers at module
boundaries). Used both directly (unit tests injecting it explicitly)
and via the `fake_storage` fixture in conftest.py (patches
apps.documents.services.get_storage_backend for view-level tests that
don't inject a backend themselves).
"""


class FakeStorageBackend:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted_keys: list[str] = []

    def upload(self, *, key: str, fileobj, content_type: str) -> None:
        self.objects[key] = fileobj.read()

    def generate_presigned_url(self, *, key: str, expires_in: int) -> str:
        return f"https://fake-storage.test/{key}?expires_in={expires_in}"

    def delete(self, *, key: str) -> None:
        self.objects.pop(key, None)
        self.deleted_keys.append(key)
