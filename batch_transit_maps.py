#!/usr/bin/env python3
"""
Batch orchestration for Magga SVG pipelines: merged / rare-first stops (EN+KN)
and route-family subsets (wildcards or regex on route_short_name).

Output layout (example)::

    OUT/
      en/stops_merged_g50/profile_default/
      kn/stops_merged_g50/profile_default/   # --indic-font-fallback on KN
      en/routes/wild_413star/
      en/routes/regex_31digit/

Part of Magga (ಮಗ್ಗ/मಗ್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from pathlib import Path
from typing import List, Optional

import partridge as ptg

from magga_style import MaggaStyle

SCRIPT_DIR = Path(__file__).resolve().parent


def _python() -> str:
    return os.environ.get("MAGGA_PYTHON", sys.executable)


def route_ids_matching_regex(gtfs_path: str, pattern: str) -> List[str]:
    """route_id list where ``route_short_name`` fully matches ``pattern``."""
    rx = re.compile(pattern)
    feed = ptg.load_feed(gtfs_path)
    r = feed.routes
    names = r["route_short_name"].fillna("").astype(str)
    mask = names.map(lambda s: bool(rx.match(s)))
    return r.loc[mask, "route_id"].astype(str).tolist()


def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "_", s)[:80]


def run_generate_all_stops(
    gtfs: Path,
    out_dir: Path,
    *,
    merge_names: bool,
    least_first: bool,
    max_groups: Optional[int],
    profile: str,
    min_trips: int,
    backdrop: bool,
    skip_existing: bool,
    indic_fonts: bool,
    geographic: bool,
    schematic: bool,
    all_station_labels: bool = False,
    workers: int = 1,
    skip_top_n: int = 0,
    flat_labels: bool = False,
) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    style_path = out_dir / "_profile_style.json"
    if profile == "compact":
        st = replace(
            MaggaStyle(),
            station_label_size=48.0,
            line_label_size=34.0,
            max_aggr_dist=220.0,
            smoothing=22.0,
            line_width=18.0,
            line_spacing=9.0,
        )
        st.save(style_path)
    else:
        MaggaStyle().save(style_path)

    cmd: List[str] = [
        _python(),
        str(SCRIPT_DIR / "generate_all_stops.py"),
        str(gtfs),
        "-o",
        str(out_dir),
        "--style",
        str(style_path),
        "-m",
        str(min_trips),
    ]
    if backdrop:
        cmd.append("--backdrop")
    if merge_names:
        cmd.append("--merge-identical-names")
    if least_first:
        cmd.append("--least-first")
    if max_groups is not None:
        cmd.extend(["--max-groups", str(max_groups)])
    if skip_existing:
        cmd.append("--skip-existing")
    if indic_fonts:
        cmd.append("--indic-font-fallback")
    cmd.append("--progressive")
    if not schematic:
        cmd.append("--geographic-only")
    if not geographic:
        cmd.append("--schematic-only")
    if all_station_labels:
        cmd.append("--all-station-labels")
    if workers > 1:
        cmd.extend(["--workers", str(workers)])
    if skip_top_n > 0:
        cmd.extend(["--skip-top-n", str(skip_top_n)])
    if flat_labels:
        cmd.append("--flat-labels")

    print(" ".join(cmd), file=sys.stderr)
    return subprocess.call(cmd)


def cmd_stops(args: argparse.Namespace) -> int:
    en = getattr(args, "en_feed", None)
    kn = getattr(args, "kn_feed", None)
    if not en and not kn:
        print("Provide --en-feed and/or --kn-feed", file=sys.stderr)
        return 1
    if args.merge_names and args.least_first:
        print("Use only one of --merge-names / --least-first", file=sys.stderr)
        return 1

    subdir = "stops"
    if args.merge_names:
        subdir += "_merged"
    if args.least_first:
        subdir += "_least_first"
    if args.max_groups is not None:
        subdir += f"_g{args.max_groups}"
    else:
        subdir += "_all"

    rc = 0
    runs: List[tuple[str, Path, bool]] = []
    if en:
        runs.append(("en", Path(en), False))
    if kn:
        runs.append(("kn", Path(kn), True))

    workers = max(1, getattr(args, "workers", 1))
    parallel_langs = getattr(args, "parallel_langs", True)

    def run_one_lang(item: tuple[str, Path, bool]) -> int:
        lang, feed, indic = item
        if not feed.is_file():
            print(f"Skip missing feed: {feed}", file=sys.stderr)
            return 0
        inner = 0
        for profile in args.profiles:
            od = Path(args.out) / lang / subdir / f"profile_{profile}"
            r = run_generate_all_stops(
                feed,
                od,
                merge_names=args.merge_names,
                least_first=args.least_first,
                max_groups=args.max_groups,
                profile=profile,
                min_trips=args.min_trips,
                backdrop=args.backdrop,
                skip_existing=args.skip_existing,
                indic_fonts=indic,
                geographic=not args.schematic_only,
                schematic=not args.geographic_only,
                all_station_labels=getattr(args, "all_station_labels", False),
                workers=workers,
                skip_top_n=getattr(args, "skip_top_n", 0),
                flat_labels=getattr(args, "flat_labels", False),
            )
            inner = inner or r
        return inner

    if len(runs) > 1 and parallel_langs:
        with ThreadPoolExecutor(max_workers=len(runs)) as ex:
            futs = [ex.submit(run_one_lang, t) for t in runs]
            for fut in as_completed(futs):
                rc = rc or fut.result()
    else:
        for t in runs:
            rc = rc or run_one_lang(t)
    return rc


def cmd_routes(args: argparse.Namespace) -> int:
    en = getattr(args, "en_feed", None)
    kn = getattr(args, "kn_feed", None)
    if not en and not kn:
        print("Provide --en-feed and/or --kn-feed", file=sys.stderr)
        return 1
    sh = SCRIPT_DIR / "process_transit_map.sh"
    if not sh.is_file():
        print(f"Missing {sh}", file=sys.stderr)
        return 1

    rc = 0
    runs: List[tuple[str, Path]] = []
    if en:
        runs.append(("en", Path(en)))
    if kn:
        runs.append(("kn", Path(kn)))

    env = os.environ.copy()
    env["MAGGA_PYTHON"] = _python()

    for lang, feed in runs:
        if not feed.is_file():
            continue
        base = Path(args.out) / lang / "routes"
        targets: List[tuple[str, List[str]]] = []

        for w in args.wildcard or []:
            slug = _slug(w.replace("*", "STAR"))
            od = str(base / f"wild_{slug}")
            targets.append(
                (
                    od,
                    [
                        "bash",
                        str(sh),
                        str(feed),
                        "-r",
                        w,
                        "-m",
                        str(args.min_trips),
                        "-lt",
                        str(args.loom_limit),
                        "-o",
                        od,
                    ],
                )
            )

        for rx in args.regex or []:
            ids = route_ids_matching_regex(str(feed), rx)
            if not ids:
                print(f"No routes for regex {rx!r} ({lang})", file=sys.stderr)
                continue
            slug = _slug(rx)
            od = str(base / f"re_{slug}")
            idstr = ",".join(ids)
            targets.append(
                (
                    od,
                    [
                        "bash",
                        str(sh),
                        str(feed),
                        "--route-ids",
                        idstr,
                        "-m",
                        str(args.min_trips),
                        "-lt",
                        str(args.loom_limit),
                        "-o",
                        od,
                    ],
                )
            )

        for od, cmd in targets:
            Path(od).parent.mkdir(parents=True, exist_ok=True)
            print(" ".join(cmd), file=sys.stderr)
            r = subprocess.call(cmd, env=env)
            rc = rc or r
    return rc


def cmd_demo(args: argparse.Namespace) -> int:
    """Tiny smoke batch: 1 merged name-group + one route wildcard."""
    args.out = str(Path(args.out) / "demo_batch")
    args.merge_names = True
    args.least_first = False
    args.max_groups = 1
    args.profiles = ["default"]
    args.backdrop = False
    args.skip_existing = True
    args.kn_feed = None
    args.geographic_only = False
    args.schematic_only = False
    if not args.en_feed:
        print("--en-feed required for demo", file=sys.stderr)
        return 1
    r1 = cmd_stops(args)
    sh = SCRIPT_DIR / "process_transit_map.sh"
    env = os.environ.copy()
    env["MAGGA_PYTHON"] = _python()
    od = str(Path(args.out) / "en" / "routes" / "top3_by_trips")
    Path(od).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "bash",
        str(sh),
        str(Path(args.en_feed).resolve()),
        "-n",
        "3",
        "-m",
        "1",
        "-lt",
        str(args.loom_limit),
        "-o",
        od,
    ]
    print(" ".join(cmd), file=sys.stderr)
    r2 = subprocess.call(cmd, env=env)
    return r1 or r2


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("stops", help="generate_all_stops batches (merged or least-first)")
    ps.add_argument("--en-feed", type=str, default=None)
    ps.add_argument("--kn-feed", type=str, default=None)
    ps.add_argument("--out", type=str, required=True, help="Base output directory")
    ps.add_argument("--merge-names", action="store_true")
    ps.add_argument("--least-first", action="store_true")
    ps.add_argument(
        "--max-groups",
        type=int,
        default=None,
        help="Cap groups (merged) or stops (least-first); e.g. 50 then 100",
    )
    ps.add_argument(
        "--profiles",
        nargs="+",
        default=["default"],
        choices=["default", "compact"],
        help="default = base MaggaStyle; compact = larger aggregation, smaller labels",
    )
    ps.add_argument("-m", "--min-trips", type=int, default=5)
    ps.add_argument("--backdrop", action="store_true")
    ps.add_argument("--skip-existing", action="store_true")
    ps.add_argument("--geographic-only", action="store_true")
    ps.add_argument("--schematic-only", action="store_true")
    ps.add_argument(
        "--all-station-labels",
        action="store_true",
        help="Pass through to generate_all_stops: show fringe/tip station names (tier 1).",
    )
    ps.add_argument(
        "--workers",
        type=int,
        default=1,
        metavar="N",
        help="Parallel stop jobs per feed (passed to generate_all_stops). Try 4–8 on M2 Pro.",
    )
    ps.add_argument(
        "--parallel-langs",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="When both EN and KN feeds are set, run those batches concurrently (default: on).",
    )
    ps.add_argument(
        "--skip-top-n",
        type=int,
        default=0,
        metavar="N",
        help="Exclude the N busiest stops by importance (pass-through to generate_all_stops).",
    )
    ps.add_argument(
        "--flat-labels",
        action="store_true",
        help="No tier split / no progressive variants (pass-through to generate_all_stops).",
    )
    ps.set_defaults(func=cmd_stops)

    pr = sub.add_parser("routes", help="process_transit_map.sh route families")
    pr.add_argument("--en-feed", type=str, default=None)
    pr.add_argument("--kn-feed", type=str, default=None)
    pr.add_argument("--out", type=str, required=True)
    pr.add_argument(
        "--wildcard",
        action="append",
        default=[],
        metavar="PATTERN",
        help="GTFS route_short_name glob (e.g. 413*) — repeatable",
    )
    pr.add_argument(
        "--regex",
        action="append",
        default=[],
        metavar="REGEX",
        help="Anchor regex on route_short_name (e.g. ^31[0-9]) — repeatable",
    )
    pr.add_argument("-m", "--min-trips", type=int, default=1)
    pr.add_argument("--loom-limit", type=int, default=600)
    pr.set_defaults(func=cmd_routes)

    pd = sub.add_parser(
        "demo",
        help="Test batch: 1 rare merged name-group + top-3 routes SVG (EN only)",
    )
    pd.add_argument("--en-feed", type=str, required=True)
    pd.add_argument("--out", type=str, default="output/batch_demo")
    pd.add_argument("-m", "--min-trips", type=int, default=5)
    pd.add_argument("--loom-limit", type=int, default=300)
    pd.set_defaults(func=cmd_demo)

    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
