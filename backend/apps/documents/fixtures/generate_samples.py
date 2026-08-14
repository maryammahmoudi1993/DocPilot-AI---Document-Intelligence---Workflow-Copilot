"""One-off generator for the synthetic sample PDFs checked into this
directory (`sample-invoice.pdf`, `sample-contract.pdf`). Not imported by
any runtime code path - re-run manually (`python generate_samples.py`
from this directory) only if the sample content needs to change.

Hand-writes minimal valid PDF syntax (single page, base-14 Helvetica -
no font embedding needed, no third-party PDF-authoring dependency added
to the project just for two static demo files) rather than pulling in
reportlab/fpdf for a one-time generation task. See fixtures/README.md
for what these files are and are not (entirely synthetic, no real
business data).
"""

from pathlib import Path


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def make_simple_pdf(lines: list[str], *, title: str) -> bytes:
    font_size = 11
    leading = 16
    x, y_start = 72, 740

    content_ops = [f"BT /F1 {font_size} Tf {leading} TL {x} {y_start} Td"]
    for i, line in enumerate(lines):
        prefix = "" if i == 0 else "T* "
        content_ops.append(f"{prefix}({_escape(line)}) Tj")
    content_ops.append("ET")
    content_stream = "\n".join(content_ops).encode("latin-1")

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        f"<< /Length {len(content_stream)} >>\nstream\n".encode("latin-1")
        + content_stream
        + b"\nendstream"
    )
    objects.append(
        f"<< /Title ({_escape(title)}) /Producer (DocPilot AI sample fixtures) >>".encode("latin-1")
    )

    buffer = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for i, body in enumerate(objects, start=1):
        offsets.append(len(buffer))
        buffer += f"{i} 0 obj\n".encode("latin-1") + body + b"\nendobj\n"

    xref_offset = len(buffer)
    buffer += f"xref\n0 {len(objects) + 1}\n".encode("latin-1")
    buffer += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        buffer += f"{offset:010d} 00000 n \n".encode("latin-1")
    buffer += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {len(objects)} 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF"
    ).encode("latin-1")

    return bytes(buffer)


INVOICE_LINES = [
    "SAMPLE INVOICE - SYNTHETIC DEMO DATA - NOT A REAL TRANSACTION",
    "",
    "Invoice #: INV-2026-0142",
    "Date: 2026-06-03",
    "Vendor: Northwind Office Supply Co. (fictional)",
    "Bill To: Demo Workspace, DocPilot AI Portfolio Project",
    "",
    "Description                          Qty   Unit Price   Amount",
    "Standing desk, adjustable             2      $410.00     $820.00",
    "Ergonomic chair                       4      $265.00    $1,060.00",
    "Monitor arm, dual                     4       $89.50      $358.00",
    "",
    "Subtotal:                                              $2,238.00",
    "Tax (8.25%):                                             $184.64",
    "Total Due:                                             $2,422.64",
    "",
    "Payment Terms: Net 30",
    "Due Date: 2026-07-03",
]

CONTRACT_LINES = [
    "SAMPLE SERVICE AGREEMENT - SYNTHETIC DEMO DATA - NOT A REAL CONTRACT",
    "",
    "Agreement #: CTR-2026-0088",
    "Effective Date: 2026-05-01",
    "",
    "Party A: DocPilot Portfolio Demo Workspace (fictional entity)",
    "Party B: Meridian Consulting Group LLC (fictional entity)",
    "",
    "1. Scope of Services",
    "Party B agrees to provide quarterly document-workflow consulting",
    "services to Party A, as described in Exhibit A (omitted - sample).",
    "",
    "2. Term",
    "This agreement is effective for twelve (12) months from the",
    "Effective Date above, renewing automatically unless either party",
    "provides thirty (30) days written notice of non-renewal.",
    "",
    "3. Fees",
    "Quarterly fee: $12,500.00, payable net 30 from invoice date.",
    "",
    "4. Signatures (sample - not executed)",
    "Party A: _____________________     Date: __________",
    "Party B: _____________________     Date: __________",
]


if __name__ == "__main__":
    out_dir = Path(__file__).parent
    (out_dir / "sample-invoice.pdf").write_bytes(
        make_simple_pdf(INVOICE_LINES, title="Sample Invoice (Synthetic Demo Data)")
    )
    (out_dir / "sample-contract.pdf").write_bytes(
        make_simple_pdf(CONTRACT_LINES, title="Sample Service Agreement (Synthetic Demo Data)")
    )
    print("Wrote sample-invoice.pdf and sample-contract.pdf")
