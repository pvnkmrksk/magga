"""Matplotlib route/trip figure."""

import pandas as pd


def test_write_route_trip_matplotlib_png_smoke(tmp_path):
    from network_route_mpl import write_route_trip_matplotlib_png

    df = pd.DataFrame(
        {
            "route_id": ["r1", "r2", "r3"],
            "route_short_name": ["A", "B", "C"],
            "trip_count": [100, 30, 5],
        }
    )
    out = tmp_path / "fig.png"
    write_route_trip_matplotlib_png(df, out, top_n=2)
    assert out.is_file()
    assert out.stat().st_size > 2000
