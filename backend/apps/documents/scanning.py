"""Malware-scanning integration interface for uploads (Phase 10 rule:
'Add malware-scanning integration interface without requiring a paid
service in tests'). Same shape as the OCR/classification provider
abstractions in apps/processing/providers.py — a `Protocol`, a default
implementation with no external dependency, and a settings-driven
factory — so a real AV engine (e.g. a ClamAV daemon reached over
`clamd`, or a hosted scanning API) can be wired in behind this same
interface later without any caller changing.

The default provider, `EicarSignatureScanProvider`, is not a general
malware scanner — it only detects the industry-standard EICAR antivirus
test string (https://www.eicar.org/download-anti-malware-testfile/),
the same file every commercial AV product recognizes for testing a
scanning path end-to-end without needing a real virus sample. That
makes it honest to run in production (it costs nothing and never false-
flags real documents) and safe to exercise in unit tests (no network
call, no paid service — the project rule this interface exists to
satisfy).
"""

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings

# The standard 68-byte EICAR test string. Deliberately not treated as a
# secret — it's public by design (see the EICAR project's own site) and
# never resembles real document content, so this constant is safe to
# read out of a log or test failure message.
EICAR_SIGNATURE = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


@dataclass(frozen=True)
class MalwareScanResult:
    is_clean: bool
    provider: str
    threat_name: str | None = None


class MalwareScanProvider(Protocol):
    def scan(self, *, fileobj) -> MalwareScanResult: ...


class EicarSignatureScanProvider:
    """Default provider — offline, deterministic, no paid service."""

    _CHUNK_SIZE = 1024 * 1024

    def scan(self, *, fileobj) -> MalwareScanResult:
        original_position = fileobj.tell()
        fileobj.seek(0)
        # Read in chunks rather than the whole file at once (same
        # streaming discipline as services.compute_sha256) — the
        # signature can't be split across a chunk boundary undetected
        # since each chunk overlaps the previous one by the signature's
        # length minus one byte.
        overlap = len(EICAR_SIGNATURE) - 1
        buffer = b""
        found = False
        while True:
            chunk = fileobj.read(self._CHUNK_SIZE)
            if not chunk:
                break
            buffer += chunk
            if EICAR_SIGNATURE in buffer:
                found = True
                break
            buffer = buffer[-overlap:] if overlap else b""
        fileobj.seek(original_position)

        if found:
            return MalwareScanResult(
                is_clean=False, provider="eicar-signature", threat_name="EICAR-Test-Signature"
            )
        return MalwareScanResult(is_clean=True, provider="eicar-signature")


class NullMalwareScanProvider:
    """Always reports clean without reading the file — an explicit
    opt-out, not a fallback, for environments where scanning should be
    disabled entirely (e.g. isolated test fixtures that intentionally
    upload the EICAR string for reasons unrelated to this check)."""

    def scan(self, *, fileobj) -> MalwareScanResult:
        return MalwareScanResult(is_clean=True, provider="null")


def get_malware_scan_provider() -> MalwareScanProvider:
    if settings.DOCUMENT_MALWARE_SCAN_PROVIDER == "null":
        return NullMalwareScanProvider()
    return EicarSignatureScanProvider()
