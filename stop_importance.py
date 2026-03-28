"""
Stop Importance — Scoring, distance computation, and tier assignment for stops.

Part of the Magga (ಮಗ್ಗ/मग्ग) project: https://github.com/pvnkmrksk/magga
License: GPL-3.0 — see LICENSE file.
"""

import math
from typing import List

import pandas as pd
from partridge.gtfs import Feed

from magga_style import MaggaStyle


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in meters between two lat/lon points."""
    R = 6_371_000  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compute_stop_importance(feed: Feed, style: MaggaStyle = None) -> pd.DataFrame:
    """Compute importance score for every stop in a GTFS feed.

    Importance = weighted combination of normalized trip count and route count.

    Args:
        feed: A loaded partridge GTFS feed.
        style: Style config (uses importance weights). Defaults to MaggaStyle().

    Returns:
        DataFrame with columns: stop_id, stop_name, stop_lat, stop_lon,
        trip_count, route_count, importance (0-1 normalized).
    """
    if style is None:
        style = MaggaStyle()

    trip_counts = (
        feed.stop_times
        .groupby("stop_id")["trip_id"]
        .nunique()
        .reset_index(name="trip_count")
    )

    route_counts = (
        feed.stop_times
        .merge(feed.trips[["trip_id", "route_id"]], on="trip_id")
        .groupby("stop_id")["route_id"]
        .nunique()
        .reset_index(name="route_count")
    )

    df = (
        feed.stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]]
        .merge(trip_counts, on="stop_id", how="left")
        .merge(route_counts, on="stop_id", how="left")
        .fillna(0)
    )

    # Normalize and compute weighted importance
    max_trips = df["trip_count"].max()
    max_routes = df["route_count"].max()
    if max_trips > 0:
        norm_trips = df["trip_count"] / max_trips
    else:
        norm_trips = 0.0
    if max_routes > 0:
        norm_routes = df["route_count"] / max_routes
    else:
        norm_routes = 0.0

    df["importance"] = (
        style.importance_trip_weight * norm_trips
        + style.importance_route_weight * norm_routes
    )

    return df.sort_values("importance", ascending=False).reset_index(drop=True)


def compute_distances_from(
    stops_df: pd.DataFrame, focal_stop_ids: List[str]
) -> pd.DataFrame:
    """Compute haversine distance from each stop to the nearest focal stop.

    Args:
        stops_df: DataFrame with stop_id, stop_lat, stop_lon columns.
        focal_stop_ids: List of stop IDs to measure distance from.

    Returns:
        DataFrame with columns: stop_id, distance_m, nearest_focal_stop.
    """
    focal = stops_df[stops_df["stop_id"].isin(focal_stop_ids)]

    results = []
    for _, stop in stops_df.iterrows():
        min_dist = float("inf")
        nearest = None
        for _, fstop in focal.iterrows():
            d = haversine(
                stop["stop_lat"], stop["stop_lon"],
                fstop["stop_lat"], fstop["stop_lon"],
            )
            if d < min_dist:
                min_dist = d
                nearest = fstop["stop_id"]
        results.append({
            "stop_id": stop["stop_id"],
            "distance_m": min_dist,
            "nearest_focal_stop": nearest,
        })

    return pd.DataFrame(results)


def assign_tiers(
    importance_df: pd.DataFrame,
    distance_df: pd.DataFrame,
    style: MaggaStyle = None,
) -> pd.DataFrame:
    """Assign display tiers to each stop based on distance and importance.

    Tier assignment logic:
      - Tier 1 (within tier_distances[0]m): all labels shown
      - Tier 2 (tier_distances[0]-[1]m): labels only if route_count >= tier2_min_routes
      - Tier 3 (tier_distances[1]-[2]m): labels only if route_count >= tier3_min_routes
      - Tier 4 (beyond tier_distances[2]m): station dot only, no label

    Args:
        importance_df: Output of compute_stop_importance().
        distance_df: Output of compute_distances_from().
        style: Style config with tier thresholds.

    Returns:
        DataFrame with columns: stop_id, stop_name, tier, distance_m,
        route_count, importance, show_label.
    """
    if style is None:
        style = MaggaStyle()

    df = importance_df.merge(distance_df[["stop_id", "distance_m"]], on="stop_id")
    d1, d2, d3 = style.tier_distances

    def _tier(row):
        dist = row["distance_m"]
        routes = row["route_count"]
        if dist <= d1:
            return 1
        elif dist <= d2:
            return 2 if routes >= style.tier2_min_routes else 4
        elif dist <= d3:
            return 3 if routes >= style.tier3_min_routes else 4
        else:
            return 4

    df["tier"] = df.apply(_tier, axis=1)
    df["show_label"] = df["tier"] <= 3

    return df.sort_values(["tier", "importance"], ascending=[True, False]).reset_index(drop=True)


def get_hf_corridor_routes(feed: Feed, min_trips: int = None, style: MaggaStyle = None) -> List[str]:
    """Extract route IDs that qualify as high-frequency corridors.

    Args:
        feed: A loaded partridge GTFS feed.
        min_trips: Minimum trips for a route to be HF. Overrides style.backdrop_min_trips.
        style: Style config (for default min_trips).

    Returns:
        List of route_id strings for high-frequency routes.
    """
    if style is None:
        style = MaggaStyle()
    if min_trips is None:
        min_trips = style.backdrop_min_trips

    route_trip_counts = feed.trips.groupby("route_id").size()
    return list(route_trip_counts[route_trip_counts >= min_trips].index)
