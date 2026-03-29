"""Tests for network_stats junction / route frequency helpers."""

import pandas as pd
import pytest

from network_stats import build_route_trip_frequency, build_stop_junction_ranking


class FakeFeed:
    """Minimal partridge-like feed with only used attributes."""

    def __init__(self, stops, trips, stop_times, routes):
        self.stops = stops
        self.trips = trips
        self.stop_times = stop_times
        self.routes = routes


@pytest.fixture
def tiny_feed():
    # Two routes, three stops; S2 is a junction (both routes)
    routes = pd.DataFrame(
        {
            "route_id": ["R1", "R2"],
            "route_short_name": ["1", "2"],
            "route_long_name": ["Line 1", "Line 2"],
        }
    )
    trips = pd.DataFrame(
        {
            "trip_id": ["T1a", "T1b", "T2a"],
            "route_id": ["R1", "R1", "R2"],
        }
    )
    stop_times = pd.DataFrame(
        {
            "trip_id": ["T1a", "T1b", "T2a", "T2a"],
            "stop_id": ["S1", "S2", "S2", "S3"],
        }
    )
    stops = pd.DataFrame(
        {
            "stop_id": ["S1", "S2", "S3"],
            "stop_name": ["A", "Junction", "C"],
            "stop_lat": [1.0, 2.0, 3.0],
            "stop_lon": [1.0, 2.0, 3.0],
        }
    )
    return FakeFeed(stops, trips, stop_times, routes)


def test_route_trip_frequency_ranks(tiny_feed):
    df = build_route_trip_frequency(tiny_feed)
    assert len(df) == 2
    r1 = df[df["route_id"] == "R1"].iloc[0]
    r2 = df[df["route_id"] == "R2"].iloc[0]
    assert int(r1["trip_count"]) == 2
    assert int(r2["trip_count"]) == 1
    assert r1["rank_by_trips"] == 1
    assert r2["rank_by_trips"] == 2
    assert r1["pctile_by_trips"] >= r2["pctile_by_trips"]


def test_stop_junction_ordering(tiny_feed):
    df = build_stop_junction_ranking(tiny_feed)
    by_j = df.sort_values("junction_order")
    # S2 has 2 routes; S1 and S3 have 1
    top = by_j.iloc[0]
    assert top["stop_id"] == "S2"
    assert top["route_count"] == 2
    assert top["junction_order"] == 1


def test_stop_percentiles_bounded(tiny_feed):
    df = build_stop_junction_ranking(tiny_feed)
    assert df["pctile_routes"].between(0, 100).all()
    assert df["pctile_trips"].between(0, 100).all()
    assert df["hub_score"].between(0, 100).all()
