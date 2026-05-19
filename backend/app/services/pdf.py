"""PDF generation service — WeasyPrint wrapper.

WeasyPrint is imported lazily inside the worker function so this module — and
the whole app — imports cleanly on machines without the native Pango/Cairo
libraries. Rendering is CPU-bound, so it runs in a worker thread and does not
block the event loop.
"""

from __future__ import annotations

import asyncio


def _render(html: str) -> bytes:
    """Render HTML to PDF bytes (blocking). Imports WeasyPrint lazily."""
    from weasyprint import HTML  # needs native libs; import only when used

    return HTML(string=html).write_pdf()


async def generate_pdf(html: str) -> bytes:
    """Render an HTML string to PDF bytes via WeasyPrint.

    Args:
        html: A complete HTML document. The mandatory disclaimer (PIS-24 #4)
            must already be present — that is the Report Agent's job.

    Returns:
        bytes: The rendered PDF.
    """
    return await asyncio.to_thread(_render, html)
