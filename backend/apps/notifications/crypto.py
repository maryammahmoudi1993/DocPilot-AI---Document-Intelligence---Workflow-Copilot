"""Symmetric encryption for webhook secrets at rest — the one place
this project stores a value that must never be recoverable through the
API once written (see WebhookEndpoint.encrypted_secret). Uses Fernet
(AES-128-CBC + HMAC, from the `cryptography` package, already a
transitive dependency of this project's JWT/TLS stack — used here
directly and explicitly rather than implicitly) rather than Django's
`django.core.signing`, which only signs (tamper-evident) and does not
encrypt (recoverable-by-anyone-with-the-payload)."""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = settings.INTEGRATION_SECRET_KEY
    if not key:
        raise ImproperlyConfigured(
            "INTEGRATION_SECRET_KEY must be set to store webhook secrets. "
            "Generate one with Fernet.generate_key()."
        )
    return Fernet(key.encode("utf-8") if isinstance(key, str) else key)


def encrypt_secret(raw_secret: str) -> bytes:
    return _fernet().encrypt(raw_secret.encode("utf-8"))


def decrypt_secret(encrypted: bytes) -> str:
    try:
        return _fernet().decrypt(encrypted).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored webhook secret could not be decrypted.") from exc
