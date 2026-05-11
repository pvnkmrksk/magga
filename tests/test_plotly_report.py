"""Smoke test for Plotly HTML network report (optional dependency)."""

import pandas as pd
import pytest


def test_write_route_trip_plotly_html_smoke(tmp_path):
    pytest.importorskip("plotly")
    from network_plotly_report import write_route_trip_plotly_html

    df = pd.DataFrame(
        {
            "route_id": ["r1", "r2", "r3"],
            "route_short_name": ["A", "B", "C"],
            "trip_count": [100, 30, 5],
        }
    )
    out = tmp_path / "rep.html"
    write_route_trip_plotly_html(df, out, top_n=2)
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert len(text) > 500
    assert "magga.kutuhula.in" in text

    df2 = df.copy()
    df2["route_display_name"] = ["ಅ", "ಬಿ", "ಸಿ"]
    out2 = tmp_path / "rep2.html"
    write_route_trip_plotly_html(df2, out2, top_n=2, label_column="route_display_name")
    text2 = out2.read_text(encoding="utf-8")
    assert "magga.kutuhula.in" in text2
    # Plotly may JSON-escape non-ASCII in the embedded figure spec
    assert "ಅ" in text2 or "\\u0c85" in text2
