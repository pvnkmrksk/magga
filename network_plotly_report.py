"""
Interactive Plotly HTML: route trip histogram, trip-coverage CDF, top-N route bars.

The CDF sorts routes by scheduled trip count (high → low) and plots cumulative
share of all trips in the feed. The last point is 100% when every route is
included — useful for seeing how small a “core” route set can be.

Part of Magga (ಮಗ್ಗ/मಗ್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


def write_route_trip_plotly_html(
    routes_df: pd.DataFrame,
    output_path: Path,
    *,
    top_n: int = 100,
    title: Optional[str] = None,
    label_column: Optional[str] = None,
) -> None:
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as e:
        raise ImportError(
            "Plotly is required for HTML reports: pip install plotly"
        ) from e

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    df = routes_df.copy()
    if "trip_count" not in df.columns:
        raise ValueError("routes_df must contain trip_count")
    df["trip_count"] = pd.to_numeric(df["trip_count"], errors="coerce").fillna(0).astype(int)
    df = df.sort_values("trip_count", ascending=False).reset_index(drop=True)

    total_trips = int(df["trip_count"].sum())
    if total_trips <= 0:
        raise ValueError("Total trip count is zero; nothing to plot")

    n_routes = len(df)
    cum = df["trip_count"].cumsum()
    pct_trips = 100.0 * cum / total_trips
    rank = pd.Series(range(1, n_routes + 1), dtype=int)
    pct_routes_included = 100.0 * rank / n_routes

    n_show = min(max(1, top_n), n_routes)

    fig = make_subplots(
        rows=3,
        cols=1,
        row_heights=[0.22, 0.28, 0.50],
        subplot_titles=(
            "Histogram: number of routes by scheduled trip count",
            "Trip coverage CDF (routes ordered by trips, busiest first)",
            f"Top {n_show} routes by scheduled trips",
        ),
        vertical_spacing=0.09,
    )

    # 1) Histogram — distribution of trip_count across routes (unsorted counts)
    nb = min(80, max(12, n_routes // 4 or 12))
    fig.add_trace(
        go.Histogram(
            x=df["trip_count"],
            nbinsx=nb,
            name="routes",
            marker_color="#636EFA",
            hovertemplate="Trip count bin: %{x}<br>Routes: %{y}<extra></extra>",
        ),
        row=1,
        col=1,
    )

    # 2) CDF — cumulative % of all feed trips vs route rank
    fig.add_trace(
        go.Scatter(
            x=rank,
            y=pct_trips,
            mode="lines",
            name="% trips covered",
            line=dict(color="#3182bd", width=2),
            hovertemplate=(
                "Route rank (busiest→): %{x}<br>"
                "% of all trips covered: %{y:.2f}<br>"
                "% of routes included: %{customdata:.2f}"
                "<extra></extra>"
            ),
            customdata=pct_routes_included,
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[1, n_routes],
            y=[90.0, 90.0],
            mode="lines",
            line=dict(color="rgba(128,128,128,0.7)", width=1, dash="dash"),
            name="90% trips",
            hoverinfo="skip",
            showlegend=True,
        ),
        row=2,
        col=1,
    )
    fig.add_trace(
        go.Scatter(
            x=[1, n_routes],
            y=[100.0, 100.0],
            mode="lines",
            line=dict(color="rgba(80,80,80,0.5)", width=1, dash="dot"),
            name="100% trips",
            hoverinfo="skip",
            showlegend=True,
        ),
        row=2,
        col=1,
    )

    # 3) Top N routes (horizontal bars)
    top = df.head(n_show)
    lbl_col = (
        label_column
        if label_column and label_column in top.columns
        else "route_short_name"
    )
    labels = top[lbl_col].astype(str).fillna("?")
    fig.add_trace(
        go.Bar(
            x=top["trip_count"],
            y=labels,
            orientation="h",
            name="trips",
            marker_color="#3182bd",
            hovertemplate="%{y}<br>Trips: %{x}<extra></extra>",
        ),
        row=3,
        col=1,
    )

    fig.update_xaxes(title_text="Scheduled trips per route", row=1, col=1)
    fig.update_xaxes(title_text="Route rank (1 = most trips)", row=2, col=1)
    fig.update_yaxes(title_text="% of all trips in feed", range=[0, 105], row=2, col=1)

    fig.update_xaxes(title_text="Trip count", row=3, col=1)
    fig.update_yaxes(autorange="reversed", row=3, col=1)

    plot_h = 320 + 380 + max(500, 14 * n_show + 80)
    fig.update_layout(
        title_text=title or "Route / trip structure",
        height=plot_h,
        margin=dict(t=80, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )

    fig.write_html(
        str(output_path),
        include_plotlyjs="cdn",
        config={"displayModeBar": True, "scrollZoom": True},
    )
