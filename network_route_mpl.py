"""
Matplotlib static figures matching the Plotly route/trip report (hist, CDF, top bars).

Part of Magga (ಮಗ್ಗ/मಗ್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _configure_indic_fonts() -> None:
    # Kannada / Indic bar labels need a font with those glyphs
    plt.rcParams.setdefault(
        "font.sans-serif",
        ["Noto Sans Kannada", "Noto Sans", "DejaVu Sans", "Arial Unicode MS", "sans-serif"],
    )


def write_route_trip_matplotlib_png(
    routes_df: pd.DataFrame,
    output_path: Path,
    *,
    top_n: int = 100,
    title: Optional[str] = None,
    label_column: Optional[str] = None,
) -> None:
    """
    Three-panel PNG: trip-count histogram, trip-coverage CDF, top-N horizontal bars.

    ``label_column`` — column for bar y-labels; default ``route_short_name``.
    """
    _configure_indic_fonts()

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
    rank = np.arange(1, n_routes + 1)

    n_show = min(max(1, top_n), n_routes)
    top = df.head(n_show)
    lbl_col = label_column if label_column and label_column in df.columns else "route_short_name"
    labels = top[lbl_col].astype(str).fillna("?")

    nb = min(80, max(12, n_routes // 4 or 12))

    fig_h = 4.0 + 4.5 + max(5.0, 0.18 * n_show + 1.5)
    hr3 = max(1.2, 0.04 * n_show + 0.5)
    fig, (ax1, ax2, ax3) = plt.subplots(
        3,
        1,
        figsize=(10, fig_h),
        height_ratios=[1.0, 1.2, hr3],
        constrained_layout=True,
    )
    ax1.hist(df["trip_count"], bins=nb, color="#636EFA", edgecolor="white", linewidth=0.5)
    ax1.set_xlabel("Scheduled trips per route")
    ax1.set_ylabel("Number of routes")
    ax1.set_title("Histogram: routes by trip count")

    ax2.plot(rank, pct_trips, color="#3182bd", linewidth=2, label="% trips covered")
    ax2.axhline(90.0, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax2.axhline(100.0, color="gray", linestyle=":", linewidth=1, alpha=0.5)
    ax2.set_xlabel("Route rank (1 = most trips)")
    ax2.set_ylabel("% of all trips in feed")
    ax2.set_ylim(0, 105)
    ax2.set_title("Trip coverage CDF (busiest routes first)")
    ax2.legend(loc="lower right", fontsize=8)

    y = np.arange(len(top))
    ax3.barh(y, top["trip_count"].values, color="#3182bd", height=0.7)
    ax3.set_yticks(y)
    ax3.set_yticklabels(labels, fontsize=8)
    ax3.invert_yaxis()
    ax3.set_xlabel("Trip count")
    ax3.set_title(f"Top {n_show} routes by scheduled trips")
    for i, v in enumerate(top["trip_count"].values):
        ax3.text(v, i, f"  {int(v)}", va="center", fontsize=7, color="#333333")

    fig.suptitle(title or "Route / trip structure", fontsize=12)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
