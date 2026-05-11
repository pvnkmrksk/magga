"""
Group GTFS stops by identical (normalized) name for merged map subsets.

Part of Magga (ಮಗ್ಗ/मಗ್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd
from partridge.gtfs import Feed


def normalize_stop_name(name: str) -> str:
    """Collapse whitespace; trim. Exact match after normalize."""
    return " ".join(str(name).split()).strip()


@dataclass
class StopNameGroup:
    normalized_name: str
    stop_ids: List[str]
    """All stop_id values sharing this name (after normalize)."""
    min_trip_count: int
    """Smallest trip_count among members — used for rare-first ordering."""
    rep_stop_id: str
    """Member with min trips (ties: lexicographically smallest id)."""


def build_stop_name_groups(feed: Feed) -> List[StopNameGroup]:
    """One group per distinct normalized stop_name; rarest-stop trip count per group."""
    trip_counts = (
        feed.stop_times.groupby("stop_id")["trip_id"]
        .nunique()
        .reset_index(name="trip_count")
    )
    df = feed.stops[["stop_id", "stop_name"]].merge(
        trip_counts, on="stop_id", how="left"
    )
    df["trip_count"] = df["trip_count"].fillna(0).astype(int)
    df["norm_name"] = df["stop_name"].map(normalize_stop_name)
    df = df[df["norm_name"] != ""]

    groups: List[StopNameGroup] = []
    for norm, g in df.groupby("norm_name", sort=False):
        ids = g["stop_id"].astype(str).tolist()
        trips = g["trip_count"].tolist()
        min_tc = min(trips)
        # representative: min trips, then smallest id
        candidates = [(t, sid) for t, sid in zip(trips, ids) if t == min_tc]
        candidates.sort(key=lambda x: x[1])
        rep = candidates[0][1]
        groups.append(
            StopNameGroup(
                normalized_name=norm,
                stop_ids=sorted(set(ids), key=str),
                min_trip_count=int(min_tc),
                rep_stop_id=rep,
            )
        )
    return groups


def sort_groups_rare_first(groups: List[StopNameGroup]) -> List[StopNameGroup]:
    """Least frequent groups first (by min_trip_count), then name for stability."""
    return sorted(
        groups,
        key=lambda g: (g.min_trip_count, g.normalized_name.casefold(), g.rep_stop_id),
    )
