"""PDF generation service — WeasyPrint wrapper.

WeasyPrint is imported lazily inside the function (Phase 5) so the module
imports cleanly in environments without the native Pango/Cairo libraries —
keeping Phase-0 test collection and app startup unaffected.
"""

from __future__ import annotations


async def generate_pdf(html: str) -> bytes:
    """Render an HTML string to PDF bytes via WeasyPrint.

    The mandatory report disclaimer (PIS-24 #4) is the Report Agent's
    responsibility and must already be present in ``html``.

    Args:
        html: A complete HTML document.

    Returns:
        bytes: The rendered PDF.

    Raises:
        NotImplementedError: Always — implemented in Phase 5.
    """
    raise NotImplementedError("PDF service — implemented in Phase 5")
