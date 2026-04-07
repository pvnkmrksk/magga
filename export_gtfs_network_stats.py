#!/usr/bin/env python3
"""
Export stop junction ranking and route trip-frequency tables from a GTFS zip.

Example:
  python export_gtfs_network_stats.py bmtc-2.zip -o output/network_stats

Outputs:
  stops_junction_ranking.csv   — route_count, trip_count, junction_order, percentiles
  routes_trip_frequency.csv    — trip_count per route, pctile, top-decile flags
  _network_stats_meta.txt      — row counts and paths

Query examples (pandas / spreadsheet):
  - Top 10% routes by trips: filter is_top_decile_trips == True or pctile_by_trips >= 90
  - Top 10% hub stops: filter is_top_decile_hub == True or hub_score >= 90
  - Sort hubs: junction_order ascending (1 = most routes, tie-broken by trips)

Part of Magga (ಮಗ್ಗ/मಗ್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

import argparse
import sys
from pathlib import Path

from network_stats import export_network_stats


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("gtfs_zip", help="Path to GTFS .zip")
    p.add_argument(
        "-o",
        "--output-dir",
        default="network_stats",
        help="Directory for CSV output (default: network_stats)",
    )
    p.add_argument(
        "--print-top-routes",
        type=int,
        metavar="N",
        help="Print top N routes by trip count to stderr after export",
    )
    args = p.parse_args()

    z = Path(args.gtfs_zip)
    if not z.is_file():
        print(f"Not found: {z}", file=sys.stderr)
        sys.exit(1)

    routes_df, stops_df = export_network_stats(z, args.output_dir)
    print(
        f"Wrote {len(stops_df)} stops → {args.output_dir}/stops_junction_ranking.csv",
        file=sys.stderr,
    )
    print(
        f"Wrote {len(routes_df)} routes → {args.output_dir}/routes_trip_frequency.csv",
        file=sys.stderr,
    )

    if args.print_top_routes:
        n = args.print_top_routes
        top = routes_df.head(n)[["route_short_name", "trip_count", "pctile_by_trips"]]
        print(f"\nTop {n} routes by trip count:", file=sys.stderr)
        print(top.to_string(index=False), file=sys.stderr)


if __name__ == "__main__":
    main()
