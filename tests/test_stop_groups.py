"""stop_groups name merging."""

import pandas as pd

from stop_groups import build_stop_name_groups, normalize_stop_name, sort_groups_rare_first


class FakeFeed:
    def __init__(self, stops, trips, stop_times):
        self.stops = stops
        self.trips = trips
        self.stop_times = stop_times


def test_normalize_stop_name():
    assert normalize_stop_name("  Foo   Bar  ") == "Foo Bar"


def test_merge_same_name():
    stops = pd.DataFrame(
        {
            "stop_id": ["a", "b", "c"],
            "stop_name": ["Main St", "Main St", "Other"],
        }
    )
    trips = pd.DataFrame({"trip_id": ["t1", "t2"], "route_id": ["r1", "r1"]})
    stop_times = pd.DataFrame(
        {
            "trip_id": ["t1", "t1", "t2", "t2"],
            "stop_id": ["a", "b", "b", "c"],
        }
    )
    feed = FakeFeed(stops, trips, stop_times)
    groups = build_stop_name_groups(feed)
    by_name = {g.normalized_name: g for g in groups}
    assert set(by_name["Main St"].stop_ids) == {"a", "b"}
    assert by_name["Other"].stop_ids == ["c"]


def test_rare_first_order():
    stops = pd.DataFrame(
        {
            "stop_id": ["x", "y"],
            "stop_name": ["Rare", "Busy"],
        }
    )
    trips = pd.DataFrame(
        {
            "trip_id": [f"t{i}" for i in range(11)],
            "route_id": ["r"] * 11,
        }
    )
    rows_y = [{"trip_id": f"t{i}", "stop_id": "y"} for i in range(10)]
    rows_x = [{"trip_id": "t10", "stop_id": "x"}]
    stop_times = pd.DataFrame(rows_y + rows_x)
    feed = FakeFeed(stops, trips, stop_times)
    groups = sort_groups_rare_first(build_stop_name_groups(feed))
    assert groups[0].normalized_name == "Rare"
