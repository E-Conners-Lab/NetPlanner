"""Tests for the Advisor markdown sanitizer in the Report Agent (AI-1, SEC-20)."""

from __future__ import annotations

from app.agents.report import _render_advisor_markdown


def test_strips_script_tags() -> None:
    html = _render_advisor_markdown("Hello\n\n<script>alert(1)</script>Goodbye")
    # The tag itself must be gone; the body text may remain but as inert text
    # (no executable tag wrapping it).
    assert "<script" not in html.lower()
    assert "</script" not in html.lower()


def test_strips_iframe_and_object_tags() -> None:
    html = _render_advisor_markdown(
        "Normal text.\n\n<iframe src='https://evil.example/x'></iframe>\n\n"
        "<object data='https://evil.example/y'></object>"
    )
    assert "<iframe" not in html.lower()
    assert "<object" not in html.lower()


def test_strips_image_with_file_uri() -> None:
    html = _render_advisor_markdown("Look\n\n![pwn](file:///etc/passwd)\n\nat this")
    assert "<img" not in html.lower()
    assert "file://" not in html.lower()
    assert "/etc/passwd" not in html


def test_strips_remote_image_url() -> None:
    html = _render_advisor_markdown("See ![ext](https://evil.example/pixel.gif)")
    assert "<img" not in html.lower()
    assert "evil.example" not in html


def test_strips_javascript_links() -> None:
    html = _render_advisor_markdown("[click me](javascript:alert(1))")
    # Either the link is stripped entirely or the href protocol is gone.
    assert "javascript:" not in html.lower()


def test_strips_onerror_attribute() -> None:
    html = _render_advisor_markdown('<p onerror="alert(1)">hi</p>')
    assert "onerror" not in html.lower()


def test_preserves_tables() -> None:
    """Markdown tables (a real Advisor output) survive sanitization."""
    md_text = (
        "| Vendor | Price |\n"
        "|---|---|\n"
        "| Cisco | $1,000 |\n"
        "| Juniper | $900 |\n"
    )
    html = _render_advisor_markdown(md_text)
    assert "<table" in html.lower()
    assert "<thead" in html.lower()
    assert "Cisco" in html
    assert "Juniper" in html


def test_preserves_lists_and_emphasis() -> None:
    md_text = "Key points:\n\n" "- **CapEx** stays the same\n" "- *OpEx* drops by 30%\n"
    html = _render_advisor_markdown(md_text)
    assert "<ul" in html.lower()
    assert "<strong" in html.lower()
    assert "<em" in html.lower()


def test_html_comments_are_dropped() -> None:
    html = _render_advisor_markdown("<!-- secret leak -->\n\nVisible text")
    assert "<!--" not in html
    assert "secret leak" not in html
    assert "Visible text" in html
