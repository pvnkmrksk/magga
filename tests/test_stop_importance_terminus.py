"""Tests for terminus detection and tier override."""

import pandas as pd
import pytest

from stop_importance import apply_terminus_tier_override, terminus_stop_ids


class FakeFeed:
    def __init__(self, stops, trips, stop_times, routes):
        self.stops = stops
        self.trips = trips
        self.stop_times = stop_times
        self.routes = routes


@pytest.fixture
def feed_with_sequence():
    routes = pd.DataFrame({"route_id": ["R1"], "route_short_name": ["1"]})
    trips = pd.DataFrame({"trip_id": ["T1"], "route_id": ["R1"]})
    stop_times = pd.DataFrame(
        {
            "trip_id": ["T1", "T1", "T1"],
            "stop_id": ["S0", "S1", "S2"],
            "stop_sequence": [1, 2, 3],
        }
    )
    stops = pd.DataFrame(
        {
            "stop_id": ["S0", "S1", "S2"],
            "stop_name": ["Start", "Mid", "End"],
            "stop_lat": [0.0, 1.0, 2.0],
            "stop_lon": [0.0, 1.0, 2.0],
        }
    )
    return FakeFeed(stops, trips, stop_times, routes)


def test_terminus_stop_ids_first_and_last(feed_with_sequence):
    t = terminus_stop_ids(feed_with_sequence)
    assert t == {"S0", "S2"}


def test_apply_terminus_tier_override():
    tier_df = pd.DataFrame(
        {
            "stop_id": ["S0", "S1", "S2"],
            "stop_name": ["A", "B", "C"],
            "tier": [4, 4, 4],
        }
    )
    out = apply_terminus_tier_override(tier_df, {"S0", "S2"})
    assert list(out.loc[out["stop_id"] == "S0", "tier"]) == [1]
    assert list(out.loc[out["stop_id"] == "S1", "tier"]) == [4]
    assert list(out.loc[out["stop_id"] == "S2", "tier"]) == [1]
