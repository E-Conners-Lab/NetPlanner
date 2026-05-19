"""Test the PDF service.

Skipped where WeasyPrint's native libraries (Pango/Cairo) are not installed —
the real rasterization is verified in Docker, which ships those libraries.
"""

from __future__ import annotations

import pytest

try:
    import weasyprint  # noqa: F401

    _WEASYPRINT_OK = True
except Exception:
    # Not just ImportError — a missing native lib raises OSError at import.
    _WEASYPRINT_OK = False


@pytest.mark.skipif(
    not _WEASYPRINT_OK, reason="WeasyPrint native libraries not installed"
)
async def test_generate_pdf_produces_pdf_bytes() -> None:
    from app.services.pdf import generate_pdf

    pdf_bytes = await generate_pdf(
        "<!DOCTYPE html><html><body><h1>NetPlanner</h1></body></html>"
    )
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500
