"""Upload validation: extension, declared MIME type, size, and — where
practical — content signature (magic bytes). Untrusted input (project
rule: treat uploaded file content as untrusted data) — nothing here
trusts the client-declared filename or content-type alone.
"""

from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

EXTENSION_CONTENT_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv",
    ".txt": "text/plain",
}

# Only checked where a reliable magic-byte signature exists — csv/txt are
# arbitrary text with no signature to check, so they're validated by
# extension/declared-type/size only ("where practical", per this
# project's scope for this phase).
CONTENT_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    # .docx/.xlsx are both zip containers — this confirms "it's a zip",
    # not which Office format specifically; that's the practical limit
    # without parsing the archive's internal manifest.
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": (b"PK\x03\x04",),
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": (b"PK\x03\x04",),
}


def validate_upload(uploaded_file) -> None:
    extension = Path(uploaded_file.name or "").suffix.lower()
    expected_content_type = EXTENSION_CONTENT_TYPES.get(extension)
    if expected_content_type is None:
        raise ValidationError(
            {"file": f"Files with extension '{extension or '(none)'}' are not allowed."}
        )

    if uploaded_file.size > settings.DOCUMENT_MAX_UPLOAD_SIZE_BYTES:
        raise ValidationError(
            {"file": f"Files must be smaller than {settings.DOCUMENT_MAX_UPLOAD_SIZE_BYTES} bytes."}
        )

    declared_type = uploaded_file.content_type
    # Some browsers/clients send application/octet-stream regardless of
    # the real type — not itself suspicious, so it's allowed through to
    # the signature check rather than rejected outright.
    if (
        declared_type
        and declared_type != expected_content_type
        and declared_type != "application/octet-stream"
    ):
        raise ValidationError({"file": "The file's declared type doesn't match its extension."})

    signatures = CONTENT_SIGNATURES.get(expected_content_type)
    if signatures:
        header = uploaded_file.read(8)
        uploaded_file.seek(0)
        if not any(header.startswith(signature) for signature in signatures):
            raise ValidationError({"file": "The file's content doesn't match its declared type."})
