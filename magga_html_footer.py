"""
Append a small branded footer to Magga-generated HTML (Folium maps, Plotly reports).

Part of the Magga (ಮಗ್ಗ/मग्ग) project.
"""

from __future__ import annotations

from pathlib import Path

MAGGA_HOME_URL = "https://magga.kutuhula.in"

_FOOTER_MARK = 'id="magga-footer"'

# UTF-8 spelling for the kutūhuḷa name; link goes to the Magga site.
_FOOTER_BLOCK = (
    '<div id="magga-footer" style="text-align:center;padding:12px 8px;font-family:system-ui,Segoe UI,sans-serif;'
    'font-size:13px;color:#555;border-top:1px solid #e0e0e0;margin-top:24px;clear:both;">'
    f'Made with <span aria-label="love">❤️</span> by <a href="{MAGGA_HOME_URL}" '
    'style="color:#3366cc;text-decoration:none;">kutūhuḷa</a></div>'
)


def append_magga_html_footer(html_path: Path | str) -> None:
    """Insert the Magga footer before ``</body>`` if not already present."""
    path = Path(html_path)
    text = path.read_text(encoding="utf-8")
    if _FOOTER_MARK in text:
        return
    needle = "</body>"
    idx = text.lower().rfind(needle)
    if idx == -1:
        path.write_text(text + "\n" + _FOOTER_BLOCK + "\n", encoding="utf-8")
        return
    injected = text[:idx] + _FOOTER_BLOCK + "\n" + text[idx:]
    path.write_text(injected, encoding="utf-8")
