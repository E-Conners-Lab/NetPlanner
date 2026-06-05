"""PDF generation service — WeasyPrint wrapper.

WeasyPrint is imported lazily inside the worker function so this module — and
the whole app — imports cleanly on machines without the native Pango/Cairo
libraries. Rendering is CPU-bound, so it runs in a worker thread and does not
block the event loop.

Resource fetching is hard-locked. ``url_fetcher`` is overridden with a "no
remote, no local" fetcher so a sanitized-but-not-deleted ``<img src=…>`` or
``@import url(…)``  cannot reach off the WeasyPrint sandbox to file:// paths,
internal hosts, or arbitrary URLs (SEC-20 / AI-1 — defense in depth on top of
the bleach pass in the Report Agent).
"""

from __future__ import annotations

import asyncio
from typing import Any


def _blocked_fetcher(url: str, _timeout: int = 10, _ssl_context: Any = None) -> dict:
    """Reject every external URL WeasyPrint asks for.

    Returning an empty SVG is the documented way to satisfy WeasyPrint while
    refusing the fetch — the renderer continues without the resource instead
    of failing the whole document.
    """
    return {
        "mime_type": "image/svg+xml",
        "string": b"<svg xmlns='http://www.w3.org/2000/svg'/>",
        "redirected_url": url,
    }


def _render(html: str) -> bytes:
    """Render HTML to PDF bytes (blocking). Imports WeasyPrint lazily."""
    from weasyprint import HTML  # needs native libs; import only when used

    # ``base_url=None`` disables relative-path resolution; ``url_fetcher`` is
    # the network-access boundary. Anything that tries to escape the document
    # is intercepted and returned as an empty SVG.
    return HTML(string=html, base_url=None, url_fetcher=_blocked_fetcher).write_pdf()


async def generate_pdf(html: str) -> bytes:
    """Render an HTML string to PDF bytes via WeasyPrint.

    Args:
        html: A complete HTML document. The mandatory disclaimer (PIS-24 #4)
            must already be present — that is the Report Agent's job.

    Returns:
        bytes: The rendered PDF.
    """
    return await asyncio.to_thread(_render, html)
