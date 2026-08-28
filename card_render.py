from __future__ import annotations

import html
from pathlib import PurePosixPath
from typing import Any


TEXT_CHAR_LIMIT = 9000
TEXT_LINE_LIMIT = 90
HTML_CHAR_LIMIT = 30000


def _truncate_text(value: str, *, char_limit: int, line_limit: int | None = None) -> tuple[str, bool]:
    truncated = False
    if line_limit is not None:
        lines = value.splitlines()
        if len(lines) > line_limit:
            value = "\n".join(lines[:line_limit])
            truncated = True
    if len(value) > char_limit:
        value = value[:char_limit]
        truncated = True
    return value, truncated


def _decode_utf8(data: bytes) -> str | None:
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _html_srcdoc(source: str) -> str:
    source, _ = _truncate_text(source, char_limit=HTML_CHAR_LIMIT)
    csp = (
        "default-src 'none'; "
        "img-src data:; "
        "style-src 'unsafe-inline'; "
        "font-src data:; "
        "media-src data:; "
        "connect-src 'none'; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    )
    prefix = (
        '<!doctype html><meta charset="utf-8">'
        f'<meta http-equiv="Content-Security-Policy" content="{html.escape(csp, quote=True)}">'
    )
    return prefix + source


def render_bytes(path: str, data: bytes) -> dict[str, Any]:
    """Return presentation-only card rendering facts for resolved bytes.

    This does not create a Canvas object type. The caller remains responsible for
    the GroundRef and object identity; this function only chooses a visual body.
    """

    suffix = PurePosixPath(path).suffix.lower()
    text = _decode_utf8(data)

    if text is not None and suffix in {".html", ".htm"}:
        source, truncated = _truncate_text(text, char_limit=HTML_CHAR_LIMIT)
        srcdoc = html.escape(_html_srcdoc(source), quote=True)
        return {
            "renderer": "html",
            "size": len(data),
            "truncated": truncated,
            "body": (
                '<div class="render-body html-render">'
                '<iframe sandbox="" referrerpolicy="no-referrer" loading="lazy" '
                f'title="Rendered HTML preview for {html.escape(path, quote=True)}" '
                f'srcdoc="{srcdoc}"></iframe>'
                '</div>'
            ),
        }

    if text is not None:
        preview, truncated = _truncate_text(
            text,
            char_limit=TEXT_CHAR_LIMIT,
            line_limit=TEXT_LINE_LIMIT,
        )
        escaped = html.escape(preview)
        more = '<div class="render-truncated">preview truncated</div>' if truncated else ""
        return {
            "renderer": "text",
            "size": len(data),
            "truncated": truncated,
            "body": (
                '<div class="render-body text-render">'
                f'<pre><code>{escaped}</code></pre>{more}'
                '</div>'
            ),
        }

    return {
        "renderer": "binary",
        "size": len(data),
        "truncated": False,
        "body": (
            '<div class="render-body binary-render">'
            '<div class="binary-glyph" aria-hidden="true">01</div>'
            f'<strong>{len(data):,} bytes</strong>'
            '<span>binary preview unavailable</span>'
            '</div>'
        ),
    }


def render_unresolved(path: str) -> dict[str, Any]:
    return {
        "renderer": "unresolved",
        "size": None,
        "truncated": False,
        "body": (
            '<div class="render-body unresolved-render">'
            '<span>bytes not resolved for this rendering</span>'
            f'<code>{html.escape(path)}</code>'
            '</div>'
        ),
    }
