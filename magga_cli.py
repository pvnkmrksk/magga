#!/usr/bin/env python3
"""
Magga unified CLI — network stats export, top-route subsets, and trip-frequency plots.

Examples
--------
  # Export ranking CSVs + plot top 50 routes + build subset zip (top 50 by trips)
  python magga_cli.py bmtc-2.zip \\
      --stats-dir output/network_stats \\
      --plot-top-routes 50 --plot-output output/routes_top50_trips.png \\
      --subset-top-routes 50 --subset-output output/subset_top50_routes.zip --subset-min-trips 1

  # Top 10%% of routes by trip count (HFR-style)
  python magga_cli.py bmtc-2.zip \\
      --subset-top-routes-pct 10 --subset-output output/subset_top10pct.zip --subset-min-trips 1

  # Stats + plot only
  python magga_cli.py bmtc-2.zip --stats-dir stats --plot-top-routes 50

  # Plotly HTML + _static.png; Kannada bar labels from bmtc-2_route_labels_kn.json beside the zip
  python magga_cli.py bmtc-2.zip --plotly-html out/r.html --kannada

  # Folium map: top 100 routes, GTFS English + Kannada in line popups (JSON beside zip or --kannada)
  python magga_cli.py bmtc-2.zip --map-html out/top100_routes.html --map-top-routes 100 --kannada

  # One pass — CSVs, Plotly+static PNG, bar chart, bilingual map (put JSON files next to the zip):
  #   <stem>_route_labels_kn.json   (route_id → Kannada)
  #   <stem>_stop_labels_kn.json    (stop_id → Kannada)
  python magga_cli.py bmtc-2.zip --kannada \\
      --stats-dir output/network_stats \\
      --plotly-html output/network_stats/routes_trip_plotly.html \\
      --plot-top-routes 100 --plot-output output/network_stats/top100_routes.png \\
      --map-html output/network_stats/top100_routes_map.html --map-top-routes 100

Part of Magga (ಮಗ್ಗ/मಗ್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

from __future__ import annotations

import argparse
import math
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import partridge as ptg

from gtfs_analysis import GTFSAnalyzer
from network_stats import build_route_trip_frequency, build_stop_junction_ranking


def plot_routes_trip_bars(
    routes_df,
    n: int,
    output_path: Path,
    title: str = "Top routes by scheduled trip count",
    *,
    label_column: Optional[str] = None,
) -> None:
    """Horizontal bar chart of the top ``n`` routes by ``trip_count``."""
    sub = routes_df.head(n).copy()
    if sub.empty:
        print("No routes to plot.", file=sys.stderr)
        return
    lbl_col = (
        label_column
        if label_column and label_column in sub.columns
        else "route_short_name"
    )
    labels = sub[lbl_col].astype(str).fillna("?")
    heights = sub["trip_count"].astype(int).values
    fig_h = max(6.0, min(48.0, 0.22 * len(sub) + 2.0))
    fig, ax = plt.subplots(figsize=(10, fig_h))
    y = range(len(sub))
    ax.barh(list(y), heights, color="#3182bd")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Unique trips in feed")
    ax.set_title(title)
    for i, v in enumerate(heights):
        ax.text(v, i, f"  {v}", va="center", fontsize=8, color="#333333")
    plt.tight_layout()
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Wrote plot → {output_path}", file=sys.stderr)


def select_top_route_ids(routes_df, n: Optional[int], pct: Optional[float]) -> List[str]:
    if n is not None and n > 0:
        return routes_df.head(n)["route_id"].astype(str).tolist()
    if pct is not None and pct > 0:
        k = max(1, int(math.ceil(len(routes_df) * (pct / 100.0))))
        return routes_df.head(k)["route_id"].astype(str).tolist()
    return []


def write_stats_tables(feed, output_dir: Path, feed_path: str) -> Tuple[object, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    routes_df = build_route_trip_frequency(feed)
    stops_df = build_stop_junction_ranking(feed)
    routes_df.to_csv(output_dir / "routes_trip_frequency.csv", index=False)
    stops_df.to_csv(output_dir / "stops_junction_ranking.csv", index=False)
    meta = {
        "feed": feed_path,
        "n_routes": len(routes_df),
        "n_stops": len(stops_df),
        "total_trips": int(routes_df["trip_count"].sum()),
    }
    (output_dir / "_network_stats_meta.txt").write_text(
        "\n".join(f"{k}: {v}" for k, v in meta.items()) + "\n",
        encoding="utf-8",
    )
    return routes_df, stops_df


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("gtfs_zip", help="Input GTFS .zip")

    p.add_argument(
        "--print-top-route-ids",
        type=int,
        default=None,
        metavar="N",
        help=(
            "Print comma-separated route_id values for the N busiest routes (stdout only). "
            "For use by process_transit_map.sh; do not combine with other magga_cli options."
        ),
    )

    p.add_argument(
        "--stats-dir",
        type=Path,
        default=None,
        help="Write routes_trip_frequency.csv and stops_junction_ranking.csv here",
    )
    p.add_argument(
        "--plot-top-routes",
        type=int,
        default=None,
        metavar="N",
        help="Save PNG bar chart of top N routes by trip count (requires matplotlib)",
    )
    p.add_argument(
        "--plot-output",
        type=Path,
        default=None,
        help="PNG path for --plot-top-routes (default: <gtfs_stem>_top{N}_routes.png)",
    )
    p.add_argument(
        "--plotly-html",
        type=Path,
        default=None,
        metavar="PATH.html",
        help="Interactive Plotly HTML: trip-count histogram, trip-coverage CDF, top routes bar",
    )
    p.add_argument(
        "--plotly-top-routes",
        type=int,
        default=100,
        metavar="N",
        help="How many routes in the Plotly bar panel (default: 100)",
    )
    p.add_argument(
        "--plot-static",
        type=Path,
        default=None,
        metavar="PATH.png",
        help=(
            "Matplotlib 3-panel PNG (hist, CDF, top routes). "
            "Default when using --plotly-html: <plotly_stem>_static.png beside the HTML"
        ),
    )
    p.add_argument(
        "--no-plot-static",
        action="store_true",
        help="With --plotly-html, do not write the companion matplotlib PNG",
    )
    p.add_argument(
        "--kannada",
        action="store_true",
        help=(
            "Use <zip_stem>_route_labels_kn.json and <zip_stem>_stop_labels_kn.json next to the zip "
            "(same JSON shape: id → string or {\"kn\",\"en\",...}); warns if expected files are missing"
        ),
    )
    p.add_argument(
        "--route-labels-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="route_id → label JSON; if set, used instead of the --kannada route-label path",
    )
    p.add_argument(
        "--stop-labels-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="stop_id → label JSON for map stop popups; if set, used instead of the --kannada stop-label path",
    )
    p.add_argument(
        "--route-label-lang",
        default="kn",
        metavar="LANG",
        help="Language key when JSON values are objects (default: kn)",
    )
    p.add_argument(
        "--map-html",
        type=Path,
        default=None,
        metavar="PATH.html",
        help=(
            "Folium map of the top N routes; route/stop popups: GTFS (EN) + KN from "
            "*_route_labels_kn.json / *_stop_labels_kn.json when present, or --kannada / explicit JSON flags"
        ),
    )
    p.add_argument(
        "--map-top-routes",
        type=int,
        default=100,
        metavar="N",
        help="How many busiest routes to draw on --map-html (default: 100)",
    )

    sub = p.add_argument_group("subset (writes a new GTFS zip)")
    sub.add_argument(
        "--subset-output",
        type=Path,
        default=None,
        help="Output path for filtered GTFS .zip",
    )
    sub.add_argument(
        "--subset-top-routes",
        type=int,
        default=None,
        metavar="N",
        help="Keep the N routes with the most scheduled trips (by route_id rank)",
    )
    sub.add_argument(
        "--subset-top-routes-pct",
        type=float,
        default=None,
        metavar="PCT",
        help="Keep top PCT%% of routes by trip count (e.g. 10 for top decile)",
    )
    sub.add_argument(
        "--subset-min-trips",
        type=int,
        default=None,
        help="After route selection, drop trips whose route has fewer than this many trips",
    )

    args = p.parse_args()
    gtfs = Path(args.gtfs_zip)
    if not gtfs.is_file():
        print(f"Not found: {gtfs}", file=sys.stderr)
        sys.exit(1)

    if args.print_top_route_ids is not None:
        if args.print_top_route_ids < 1:
            p.error("--print-top-route-ids must be >= 1")
        if any(
            [
                args.stats_dir,
                args.plot_top_routes is not None,
                args.plotly_html,
                args.plot_static,
                args.no_plot_static,
                args.map_html,
                args.subset_output,
                args.subset_top_routes,
                args.subset_top_routes_pct is not None,
                args.kannada,
                args.route_labels_json,
                args.stop_labels_json,
            ]
        ):
            p.error("--print-top-route-ids cannot be combined with other options")
        feed = ptg.load_feed(str(gtfs))
        routes_df = build_route_trip_frequency(feed)
        ids = select_top_route_ids(routes_df, args.print_top_route_ids, None)
        print(",".join(ids))
        return

    need_feed = bool(
        args.stats_dir
        or args.plot_top_routes
        or args.plotly_html
        or args.map_html
        or args.subset_top_routes
        or args.subset_top_routes_pct
    )
    if not need_feed:
        p.error(
            "Provide at least one of: --stats-dir, --plot-top-routes, --plotly-html, --map-html, "
            "--subset-top-routes / --subset-top-routes-pct (with --subset-output when subsetting)"
        )

    if (args.subset_top_routes or args.subset_top_routes_pct is not None) and not args.subset_output:
        p.error("--subset-output is required when using --subset-top-routes or --subset-top-routes-pct")

    if args.subset_output and not args.subset_top_routes and args.subset_top_routes_pct is None:
        p.error("With --subset-output, add --subset-top-routes N or --subset-top-routes-pct PCT")

    if args.subset_top_routes and args.subset_top_routes_pct is not None:
        p.error("Use only one of --subset-top-routes and --subset-top-routes-pct")

    if args.plot_top_routes is not None and args.plot_top_routes < 1:
        p.error("--plot-top-routes must be >= 1")

    if args.plotly_top_routes < 1:
        p.error("--plotly-top-routes must be >= 1")

    if args.map_top_routes < 1:
        p.error("--map-top-routes must be >= 1")

    if args.route_labels_json is not None and not args.route_labels_json.is_file():
        p.error(f"--route-labels-json not found: {args.route_labels_json}")

    if args.stop_labels_json is not None and not args.stop_labels_json.is_file():
        p.error(f"--stop-labels-json not found: {args.stop_labels_json}")

    if args.plot_static is not None and not args.plotly_html:
        p.error("--plot-static requires --plotly-html")
    if args.no_plot_static and not args.plotly_html:
        p.error("--no-plot-static only applies with --plotly-html")

    routes_df = None
    feed = None
    if need_feed:
        feed = ptg.load_feed(str(gtfs))

    if args.stats_dir:
        routes_df, _stops_df = write_stats_tables(
            feed, args.stats_dir, str(gtfs.resolve())
        )
        print(f"Wrote stats → {args.stats_dir}", file=sys.stderr)

    if routes_df is None and (
        args.plot_top_routes
        or args.plotly_html
        or args.map_html
        or args.subset_top_routes
        or args.subset_top_routes_pct
    ):
        routes_df = build_route_trip_frequency(feed)

    # Explicit JSON wins; --kannada uses default path; --map-html also uses default path if file exists.
    label_json_path: Optional[Path] = None
    if args.route_labels_json is not None:
        label_json_path = args.route_labels_json
    elif args.kannada:
        label_json_path = gtfs.parent / f"{gtfs.stem}_route_labels_kn.json"
    elif args.map_html:
        _cand = gtfs.parent / f"{gtfs.stem}_route_labels_kn.json"
        if _cand.is_file():
            label_json_path = _cand

    stop_label_json_path: Optional[Path] = None
    if args.stop_labels_json is not None:
        stop_label_json_path = args.stop_labels_json
    elif args.kannada:
        stop_label_json_path = gtfs.parent / f"{gtfs.stem}_stop_labels_kn.json"
    elif args.map_html:
        _sc = gtfs.parent / f"{gtfs.stem}_stop_labels_kn.json"
        if _sc.is_file():
            stop_label_json_path = _sc

    if stop_label_json_path is not None and not stop_label_json_path.is_file():
        if args.kannada and args.stop_labels_json is None:
            print(
                f"Warning: --kannada but no stop label file: {stop_label_json_path}",
                file=sys.stderr,
            )

    route_label_column: Optional[str] = None
    routes_plot_df = routes_df
    if label_json_path is not None:
        if not label_json_path.is_file():
            if args.kannada:
                print(
                    f"Warning: --kannada but no label file: {label_json_path}",
                    file=sys.stderr,
                )
        else:
            from route_labels import load_route_label_map, merge_route_display_labels

            mapping = load_route_label_map(
                label_json_path, lang=args.route_label_lang
            )
            routes_plot_df = routes_df.copy()
            routes_plot_df["route_display_name"] = merge_route_display_labels(
                routes_plot_df, mapping
            )
            route_label_column = "route_display_name"

    if args.plotly_html:
        from network_plotly_report import write_route_trip_plotly_html

        write_route_trip_plotly_html(
            routes_plot_df,
            args.plotly_html,
            top_n=args.plotly_top_routes,
            title=f"Route / trip structure — {gtfs.name}",
            label_column=route_label_column,
        )
        print(f"Wrote Plotly HTML → {args.plotly_html}", file=sys.stderr)

        if not args.no_plot_static:
            from network_route_mpl import write_route_trip_matplotlib_png

            static_out = args.plot_static
            if static_out is None:
                static_out = args.plotly_html.with_name(
                    f"{args.plotly_html.stem}_static.png"
                )
            write_route_trip_matplotlib_png(
                routes_plot_df,
                static_out,
                top_n=args.plotly_top_routes,
                title=f"Route / trip structure — {gtfs.name}",
                label_column=route_label_column,
            )
            print(f"Wrote static plot → {static_out}", file=sys.stderr)

    if args.plot_top_routes:
        out = args.plot_output
        if out is None:
            out = gtfs.with_name(f"{gtfs.stem}_top{args.plot_top_routes}_routes.png")
        plot_routes_trip_bars(
            routes_plot_df,
            args.plot_top_routes,
            out,
            title=f"Top {args.plot_top_routes} routes by trip count",
            label_column=route_label_column,
        )

    if args.map_html:
        from gtfs_map_viewer import GTFSMapCreator, build_route_bilingual_popup_html
        from route_labels import load_route_label_map

        top_ids = select_top_route_ids(routes_df, args.map_top_routes, None)
        kn_map: dict[str, str] = {}
        if label_json_path is not None and label_json_path.is_file():
            kn_map = load_route_label_map(label_json_path, lang="kn")
        kn_stop_map: dict[str, str] = {}
        if stop_label_json_path is not None and stop_label_json_path.is_file():
            kn_stop_map = load_route_label_map(stop_label_json_path, lang="kn")

        map_bilingual_ui = bool(args.kannada or kn_map or kn_stop_map)

        tmp = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            analyzer = GTFSAnalyzer(str(gtfs))
            analyzer.create_subset(output_path=tmp_path, route_ids=top_ids, min_trips=None)
            map_creator = GTFSMapCreator(tmp_path)
            map_creator.load_gtfs_data()
            popups = build_route_bilingual_popup_html(map_creator.routes_df, kn_map or None)
            map_creator.create_map(
                output_path=str(args.map_html),
                color_by="trips",
                cmap="magma",
                route_cmap="tab20c",
                route_line_popup_html=popups,
                kn_by_stop_id=kn_stop_map if kn_stop_map else None,
                map_bilingual_ui=map_bilingual_ui,
            )
            print(
                f"Wrote route map ({len(top_ids)} routes, {len(kn_map)} route KN, "
                f"{len(kn_stop_map)} stop KN) → {args.map_html}",
                file=sys.stderr,
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    if args.subset_output:
        rids = select_top_route_ids(
            routes_df,
            args.subset_top_routes,
            args.subset_top_routes_pct,
        )
        if not rids:
            p.error(
                "Subset requested without route selection: add --subset-top-routes N "
                "or --subset-top-routes-pct PCT"
            )
        analyzer = GTFSAnalyzer(str(gtfs))
        analyzer.create_subset(
            output_path=str(args.subset_output),
            route_ids=rids,
            min_trips=args.subset_min_trips,
        )
        print(
            f"Wrote subset ({len(rids)} routes) → {args.subset_output}",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
