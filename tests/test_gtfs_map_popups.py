"""Bilingual route popup HTML for Folium."""

import pandas as pd

from gtfs_map_viewer import (
    build_route_bilingual_popup_html,
    format_stop_bilingual_popup_html,
)


def test_bilingual_popup_en_and_kn():
    df = pd.DataFrame(
        {
            "route_id": ["r1", "r2"],
            "route_short_name": ["501A", "MF-1"],
            "route_long_name": ["Majestic – Whitefield", ""],
        }
    )
    kn = {"r1": "ಮೈಸೂರು ರಸ್ತೆ"}
    html = build_route_bilingual_popup_html(df, kn)
    assert "501A" in html["r1"]
    assert "Majestic" in html["r1"]
    assert "ಮೈಸೂರು" in html["r1"]
    assert "MF-1" in html["r2"]
    assert "ಮೈಸೂರು" not in html["r2"]


def test_stop_popup_kn():
    html = format_stop_bilingual_popup_html(
        "Majestic", "S12345", 40, 12, kn_stop_name="ಮ್ಯಾಜೆಸ್ಟಿಕ್"
    )
    assert "Majestic" in html
    assert "ಮ್ಯಾಜೆಸ್ಟಿಕ್" in html
    assert "40" in html


def test_bilingual_popup_escape():
    df = pd.DataFrame(
        {
            "route_id": ["x"],
            "route_short_name": ['<script>'],
            "route_long_name": [None],
        }
    )
    html = build_route_bilingual_popup_html(df, {"x": "<b>kn</b>"})
    assert "<script>" not in html["x"]
    assert "&lt;script&gt;" in html["x"]
    assert "<b>kn</b>" not in html["x"]
    assert "&lt;b&gt;kn&lt;/b&gt;" in html["x"]
