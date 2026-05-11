"""
GTFS network statistics for stop junction ranking and route trip frequencies.

Use the exported CSVs to filter e.g. top-decile routes (HFR) or hub stops.

Part of Magga (ಮಗ್ಗ/मಗ್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple, Union

import pandas as pd
from partridge.gtfs import Feed


def build_route_trip_frequency(feed: Feed) -> pd.DataFrame:
    """Per-route trip counts with rank and percentile for HFR-style cuts."""
    trip_count = (
        feed.trips.groupby("route_id", as_index=False)
        .size()
        .rename(columns={"size": "trip_count"})
    )
    df = feed.routes.merge(trip_count, on="route_id", how="left").fillna({"trip_count": 0})
    df["trip_count"] = df["trip_count"].astype(int)
    df = df.sort_values("trip_count", ascending=False).reset_index(drop=True)

    n = len(df)
    total_trips = int(df["trip_count"].sum()) or 1
    df["trip_share_of_network"] = df["trip_count"] / total_trips
    df["rank_by_trips"] = range(1, n + 1)
    # Percentile by trip frequency (100 = busiest route)
    df["pctile_by_trips"] = df["trip_count"].rank(pct=True, method="max") * 100.0
    df["is_top_decile_trips"] = df["pctile_by_trips"] >= 90.0
    df["is_top_quartile_trips"] = df["pctile_by_trips"] >= 75.0
    return df


def build_stop_junction_ranking(feed: Feed) -> pd.DataFrame:
    """Per-stop unique trip and route counts, junction ordering, and percentiles."""
    trip_counts = (
        feed.stop_times.groupby("stop_id")["trip_id"]
        .nunique()
        .reset_index(name="trip_count")
    )
    route_counts = (
        feed.stop_times.merge(feed.trips[["trip_id", "route_id"]], on="trip_id")
        .groupby("stop_id")["route_id"]
        .nunique()
        .reset_index(name="route_count")
    )
    df = (
        feed.stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]]
        .merge(trip_counts, on="stop_id", how="left")
        .merge(route_counts, on="stop_id", how="left")
        .fillna({"trip_count": 0, "route_count": 0})
    )
    df["trip_count"] = df["trip_count"].astype(int)
    df["route_count"] = df["route_count"].astype(int)

    # Independent ranks (1 = highest)
    df["rank_by_unique_trips"] = df["trip_count"].rank(ascending=False, method="min").astype(int)
    df["rank_by_routes"] = df["route_count"].rank(ascending=False, method="min").astype(int)

    # Junction order: primary = more distinct routes, secondary = more trips
    df = df.sort_values(
        ["route_count", "trip_count"],
        ascending=[False, False],
        kind="mergesort",
    ).reset_index(drop=True)
    df["junction_order"] = range(1, len(df) + 1)

    df["pctile_routes"] = df["route_count"].rank(pct=True, method="max") * 100.0
    df["pctile_trips"] = df["trip_count"].rank(pct=True, method="max") * 100.0
    df["hub_score"] = (df["pctile_routes"] + df["pctile_trips"]) / 2.0
    df["is_top_decile_hub"] = df["hub_score"] >= 90.0

    return df


def export_network_stats(
    feed_path: Union[str, Path], output_dir: Union[str, Path]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load GTFS zip, write stop + route CSVs, return both frames."""
    import partridge as ptg

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    feed = ptg.load_feed(str(feed_path))

    routes_df = build_route_trip_frequency(feed)
    stops_df = build_stop_junction_ranking(feed)

    routes_path = output_dir / "routes_trip_frequency.csv"
    stops_path = output_dir / "stops_junction_ranking.csv"
    routes_df.to_csv(routes_path, index=False)
    stops_df.to_csv(stops_path, index=False)

    # Short manifest for quick grep / downstream tools
    meta = {
        "feed": str(Path(feed_path).resolve()),
        "n_routes": len(routes_df),
        "n_stops": len(stops_df),
        "total_trips": int(routes_df["trip_count"].sum()),
        "routes_csv": str(routes_path.resolve()),
        "stops_csv": str(stops_path.resolve()),
    }
    (output_dir / "_network_stats_meta.txt").write_text(
        "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n",
        encoding="utf-8",
    )

    return routes_df, stops_df
