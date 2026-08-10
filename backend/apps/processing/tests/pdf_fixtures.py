"""Builds small, real, structurally-valid PDFs for processing-pipeline
tests — pypdf's PdfReader actually parses these (unlike the minimal
`%PDF-1.4\\n...` byte strings apps/documents/tests use, which only need
to pass a magic-byte check, not real parsing). No extra test dependency:
built with pypdf itself (already a runtime dependency — see pyproject.toml).
"""

import io

from pypdf import PdfWriter


def _hand_written_pdf(page_texts: list[str]) -> bytes:
    """Hand-writes a minimal multi-page PDF with a real content stream
    per page (`Tj` text-showing operator), so `page.extract_text()`
    returns real, non-empty text for pages with non-empty `page_texts`
    entries, and empty text for pages with an empty string — simulating
    a page with no digital text layer (i.e. a scanned page) without
    needing a real scanned-image fixture.
    """
    objects: list[bytes] = []
    page_count = len(page_texts)

    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(page_count))
    objects.append(f"2 0 obj<< /Type /Pages /Kids [{kids}] /Count {page_count} >>endobj\n".encode())

    font_obj_num = 3 + 2 * page_count
    for i, text in enumerate(page_texts):
        page_obj_num = 3 + 2 * i
        content_obj_num = page_obj_num + 1
        objects.append(
            f"{page_obj_num} 0 obj<< /Type /Page /Parent 2 0 R "
            f"/Resources << /Font << /F1 {font_obj_num} 0 R >> >> "
            f"/MediaBox [0 0 612 792] /Contents {content_obj_num} 0 R >>endobj\n".encode()
        )
        escaped = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        stream_content = f"BT /F1 12 Tf 72 712 Td ({escaped}) Tj ET".encode("latin-1")
        objects.append(
            f"{content_obj_num} 0 obj<< /Length {len(stream_content)} >>stream\n".encode()
            + stream_content
            + b"\nendstream endobj\n"
        )

    font_obj = f"{font_obj_num} 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
    objects.append(font_obj.encode())

    header = b"%PDF-1.4\n"
    body = b""
    offsets = [0]
    pos = len(header)
    for obj in objects:
        offsets.append(pos)
        body += obj
        pos += len(obj)

    xref_pos = len(header) + len(body)
    object_count = len(objects) + 1
    xref = f"xref\n0 {object_count}\n0000000000 65535 f \n".encode()
    for offset in offsets[1:]:
        xref += f"{offset:010d} 00000 n \n".encode()
    trailer = (
        f"trailer<< /Size {object_count} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode()
    )

    return header + body + xref + trailer


def digital_pdf_bytes(text: str = "Invoice INV-1001 total due 250.00 net 30") -> bytes:
    """A one-page PDF with a real, extractable text layer."""
    return _hand_written_pdf([text])


def scanned_pdf_bytes() -> bytes:
    """A one-page PDF with no text layer — pypdf's `extract_text()`
    returns "" for it, which is exactly what a real scanned (image-only)
    page also produces; the pipeline can't and shouldn't tell the
    difference by content-stream inspection, only by extracted length."""
    return _hand_written_pdf([""])


def mixed_pdf_bytes() -> bytes:
    """Three pages: digital, scanned, digital — exercises the
    "mixed digital/scanned pages" path (only the scanned one should be
    routed to OCR)."""
    return _hand_written_pdf(
        ["Page one has real text content here.", "", "Page three also has real text."]
    )


def corrupt_pdf_bytes() -> bytes:
    return b"%PDF-1.4\nthis is not a valid pdf body\n%%EOF"


def password_protected_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt(user_password="secret", owner_password="secret-owner")  # noqa: S106 - test fixture only
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()
