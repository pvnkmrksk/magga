#!/usr/bin/env python3
"""
Generate All Stops — Batch-generate transit maps for every stop in a GTFS feed.

Produces geographic + schematic SVGs with semantic layers, progressive label
hiding, and optional HF corridor backdrops. Output is designer-ready SVG with
Inkscape-compatible layer groups.

Part of the Magga (ಮಗ್ಗ/मग्ग) project: https://github.com/pvnkmrksk/magga
License: GPL-3.0 — see LICENSE file.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import partridge as ptg

from adjust_svg import adjust_svg_text_sizes
from gtfs_analysis import GTFSAnalyzer
from magga_style import MaggaStyle
from stop_importance import (
    assign_tiers,
    compute_distances_from,
    compute_stop_importance,
    get_hf_corridor_routes,
)
from svg_layers import add_svg_layers, apply_progressive_hiding, compose_with_backdrop


def find_pipeline_tools() -> str:
    """Find the directory containing C++ pipeline tools (gtfs2graph, topo, etc).

    Checks: ./build/, then PATH.
    Returns the directory path, or exits with an error.
    """
    # Check ./build/ relative to this script
    script_dir = Path(__file__).resolve().parent
    build_dir = script_dir / "build"
    if (build_dir / "gtfs2graph").exists():
        return str(build_dir)

    # Check PATH
    if shutil.which("gtfs2graph"):
        return ""  # Already in PATH

    print(
        "Error: C++ pipeline tools not found.\n"
        "Either build them (mkdir build && cd build && cmake .. && make -j)\n"
        "or add them to PATH: export PATH=/path/to/magga/build:$PATH",
        file=sys.stderr,
    )
    sys.exit(1)


def run_pipeline(
    gtfs_zip: str,
    output_svg: str,
    style: MaggaStyle,
    schematic: bool = False,
    tool_dir: str = "",
) -> bool:
    """Run the C++ pipeline to generate a single SVG map.

    Args:
        gtfs_zip: Path to a GTFS zip file.
        output_svg: Path to write the output SVG.
        style: Style configuration.
        schematic: If True, include octi step for schematic layout.
        tool_dir: Directory containing C++ tools (prepended to PATH).

    Returns:
        True if pipeline succeeded, False otherwise.
    """
    env = os.environ.copy()
    if tool_dir:
        env["PATH"] = f"{tool_dir}:{env.get('PATH', '')}"

    topo_flags = style.to_topo_flags()
    tm_flags = style.to_transitmap_flags()
    g2g_flags = style.to_gtfs2graph_flags()

    if schematic:
        cmd = f"gtfs2graph {g2g_flags} {gtfs_zip} | topo {topo_flags} | loom | octi | transitmap {tm_flags}"
    else:
        cmd = f"gtfs2graph {g2g_flags} {gtfs_zip} | topo {topo_flags} | loom | transitmap {tm_flags}"

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            env=env,
            timeout=300,
        )
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            print(f"  Pipeline error: {stderr[:200]}", file=sys.stderr)
            return False

        Path(output_svg).parent.mkdir(parents=True, exist_ok=True)
        with open(output_svg, "wb") as f:
            f.write(result.stdout)
        return True

    except subprocess.TimeoutExpired:
        print("  Pipeline timed out (300s)", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  Pipeline failed: {e}", file=sys.stderr)
        return False


def generate_hf_backdrop(
    gtfs_path: str,
    output_dir: Path,
    style: MaggaStyle,
    tool_dir: str,
    geographic: bool = True,
    schematic: bool = True,
) -> dict:
    """Generate the shared HF corridor backdrop SVGs.

    Returns dict with keys 'geographic' and/or 'schematic' mapping to paths.
    """
    print("Generating HF corridor backdrop...", file=sys.stderr)
    feed = ptg.load_feed(gtfs_path)
    hf_routes = get_hf_corridor_routes(feed, style=style)

    if not hf_routes:
        # If no routes meet the HF threshold, lower it
        min_trips = max(1, style.backdrop_min_trips // 5)
        hf_routes = get_hf_corridor_routes(feed, min_trips=min_trips)
        if not hf_routes:
            print("  No routes qualify for HF backdrop.", file=sys.stderr)
            return {}

    # Get route short names for the pattern
    route_names = feed.routes[feed.routes["route_id"].isin(hf_routes)][
        "route_short_name"
    ].tolist()
    patterns = ",".join(str(n) for n in route_names if n)

    # Create HF subset
    analyzer = GTFSAnalyzer(gtfs_path)
    hf_subset_path = str(output_dir / "_hf_corridor.zip")
    try:
        analyzer.create_subset(
            output_path=hf_subset_path,
            route_patterns=route_names if route_names else None,
            min_trips=style.backdrop_min_trips,
        )
    except Exception as e:
        print(f"  HF subset failed: {e}", file=sys.stderr)
        return {}

    results = {}
    if geographic:
        geo_path = str(output_dir / "_hf_corridor_geographic.svg")
        if run_pipeline(hf_subset_path, geo_path, style, schematic=False, tool_dir=tool_dir):
            results["geographic"] = Path(geo_path)
            print(f"  Created {geo_path}", file=sys.stderr)

    if schematic:
        sch_path = str(output_dir / "_hf_corridor_schematic.svg")
        if run_pipeline(hf_subset_path, sch_path, style, schematic=True, tool_dir=tool_dir):
            results["schematic"] = Path(sch_path)
            print(f"  Created {sch_path}", file=sys.stderr)

    return results


def process_single_stop(
    gtfs_path: str,
    stop_id: str,
    stop_name: str,
    output_dir: Path,
    style: MaggaStyle,
    tool_dir: str,
    tier_data: dict,
    backdrop_paths: dict,
    geographic: bool = True,
    schematic: bool = True,
    progressive: bool = True,
) -> bool:
    """Generate all map variants for a single stop.

    Returns True if at least one map was generated successfully.
    """
    # Clean name for directory
    clean_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in stop_name)
    clean_name = clean_name.strip().replace(" ", "_")[:60]
    stop_dir = output_dir / f"{stop_id}_{clean_name}"
    stop_dir.mkdir(parents=True, exist_ok=True)

    # Create GTFS subset for this stop
    analyzer = GTFSAnalyzer(gtfs_path)
    subset_path = str(stop_dir / "subset.zip")
    try:
        analyzer.create_subset(
            output_path=subset_path,
            stop_ids=[stop_id],
        )
    except Exception as e:
        print(f"  Subset failed for {stop_id}: {e}", file=sys.stderr)
        return False

    success = False
    map_types = []
    if geographic:
        map_types.append(("geographic", False))
    if schematic:
        map_types.append(("schematic", True))

    for map_name, is_schematic in map_types:
        raw_svg = str(stop_dir / f"_{map_name}_raw.svg")
        layered_svg = str(stop_dir / f"{map_name}.svg")

        # Run C++ pipeline
        if not run_pipeline(subset_path, raw_svg, style, schematic=is_schematic, tool_dir=tool_dir):
            continue

        # Apply text shrink
        adjusted_svg = str(stop_dir / f"_{map_name}_adjusted.svg")
        try:
            adjust_svg_text_sizes(raw_svg, adjusted_svg, style.text_shrink)
        except Exception:
            adjusted_svg = raw_svg

        # Add semantic layers with tier data
        try:
            add_svg_layers(adjusted_svg, layered_svg, tier_data=tier_data, style=style)
        except Exception as e:
            print(f"  Layer processing failed for {stop_id}/{map_name}: {e}", file=sys.stderr)
            # Fall back to adjusted SVG
            shutil.copy(adjusted_svg, layered_svg)

        success = True

        # Generate progressive hiding variants
        if progressive and tier_data:
            try:
                apply_progressive_hiding(layered_svg, stop_dir, base_name=map_name)
            except Exception as e:
                print(f"  Progressive hiding failed for {stop_id}/{map_name}: {e}", file=sys.stderr)

        # Compose with backdrop
        backdrop_svg = backdrop_paths.get(map_name)
        if backdrop_svg and backdrop_svg.exists():
            composed_path = str(stop_dir / f"{map_name}_with_backdrop.svg")
            try:
                compose_with_backdrop(layered_svg, str(backdrop_svg), composed_path, style)
            except Exception as e:
                print(f"  Backdrop composition failed for {stop_id}/{map_name}: {e}", file=sys.stderr)

        # Clean up intermediate files
        for tmp in [raw_svg, adjusted_svg]:
            try:
                os.remove(tmp)
            except OSError:
                pass

    # Write stop metadata
    info = {
        "stop_id": stop_id,
        "stop_name": stop_name,
        "tiers": {name: tier for name, tier in tier_data.items()} if tier_data else {},
    }
    with open(stop_dir / "stop_info.json", "w") as f:
        json.dump(info, f, indent=2)

    return success


def main():
    parser = argparse.ArgumentParser(
        description="""
Magga Stop Map Generator — Batch-generate transit maps for every stop.

Produces geographic and/or schematic SVGs with:
  - Semantic SVG layers (Inkscape-compatible)
  - Progressive label hiding (nearby → important → junctions → minimal)
  - Optional HF corridor backdrop for city-wide context
  - Designer-ready output with configurable styles
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("gtfs_file", help="Path to input GTFS zip file")

    # Output
    out_group = parser.add_argument_group("output")
    out_group.add_argument(
        "-o", "--output-dir", default="stop_maps",
        help="Base output directory (default: stop_maps)",
    )

    # Selection
    sel_group = parser.add_argument_group("stop selection")
    sel_group.add_argument(
        "-n", "--top-n", type=int, default=None,
        help="Only generate maps for the top N stops by importance",
    )
    sel_group.add_argument(
        "--stops", default=None,
        help="Comma-separated stop IDs to process (default: all)",
    )
    sel_group.add_argument(
        "-m", "--min-trips", type=int, default=5,
        help="Min trips for route inclusion in subsets (default: 5)",
    )

    # Features
    feat_group = parser.add_argument_group("features")
    feat_group.add_argument(
        "--backdrop", action="store_true",
        help="Include HF corridor backdrop layer",
    )
    feat_group.add_argument(
        "--progressive", action="store_true",
        help="Generate progressive hiding variants (full/important/junctions/minimal)",
    )
    feat_group.add_argument(
        "--geographic-only", action="store_true",
        help="Skip schematic maps",
    )
    feat_group.add_argument(
        "--schematic-only", action="store_true",
        help="Skip geographic maps",
    )

    # Style
    style_group = parser.add_argument_group("style")
    style_group.add_argument(
        "--style", default=None,
        help="Path to style config JSON file",
    )
    style_group.add_argument(
        "--save-style", action="store_true",
        help="Save the effective style config to the output directory",
    )

    parser.epilog = """
examples:
  # Generate maps for all stops
  %(prog)s city_transit.zip

  # Top 10 stops with backdrop and progressive hiding
  %(prog)s city_transit.zip -n 10 --backdrop --progressive

  # Specific stops, geographic only
  %(prog)s city_transit.zip --stops "STOP1,STOP2,STOP3" --geographic-only

  # Custom style
  %(prog)s city_transit.zip --style my_style.json -n 5

  # Save default style for editing
  %(prog)s city_transit.zip --save-style -n 1

notes:
  - C++ tools (gtfs2graph, topo, loom, octi, transitmap) must be built first
  - SVG layers are Inkscape-compatible (Edit → Layers panel)
  - Style config is a JSON file; use --save-style to generate a template
  - Progressive hiding creates variants with different label density
  - HF corridor backdrop provides city-wide context at low opacity

For more information: https://github.com/pvnkmrksk/magga
"""

    args = parser.parse_args()

    # Validate input
    if not Path(args.gtfs_file).exists():
        print(f"Error: {args.gtfs_file} not found", file=sys.stderr)
        sys.exit(1)

    # Find pipeline tools
    tool_dir = find_pipeline_tools()

    # Load style
    style = MaggaStyle.from_file_or_default(args.style)

    # Setup output
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save style if requested
    if args.save_style:
        style_path = output_dir / "_style.json"
        style.save(style_path)
        print(f"Style saved to {style_path}", file=sys.stderr)

    # Map type flags
    do_geographic = not args.schematic_only
    do_schematic = not args.geographic_only

    # Compute stop importance
    print("Computing stop importance...", file=sys.stderr)
    feed = ptg.load_feed(args.gtfs_file)
    importance_df = compute_stop_importance(feed, style)

    # Save importance ranking
    importance_df.to_csv(output_dir / "_stop_importance.csv", index=False)
    print(f"  {len(importance_df)} stops scored", file=sys.stderr)

    # Select stops to process
    if args.stops:
        stop_ids = [s.strip() for s in args.stops.split(",")]
        stops_to_process = importance_df[importance_df["stop_id"].isin(stop_ids)]
    elif args.top_n:
        stops_to_process = importance_df.head(args.top_n)
    else:
        stops_to_process = importance_df

    print(f"  Processing {len(stops_to_process)} stops", file=sys.stderr)

    # Generate HF backdrop if requested
    backdrop_paths = {}
    if args.backdrop:
        backdrop_paths = generate_hf_backdrop(
            args.gtfs_file,
            output_dir,
            style,
            tool_dir,
            geographic=do_geographic,
            schematic=do_schematic,
        )

    # Process each stop
    success_count = 0
    for idx, row in stops_to_process.iterrows():
        stop_id = row["stop_id"]
        stop_name = row["stop_name"]
        print(f"\n[{idx + 1}/{len(stops_to_process)}] {stop_name} ({stop_id})", file=sys.stderr)

        # Compute distances and tiers for this stop
        distance_df = compute_distances_from(importance_df, [stop_id])
        tier_df = assign_tiers(importance_df, distance_df, style)

        # Build tier_data dict: station_name → tier
        tier_data = dict(zip(tier_df["stop_name"], tier_df["tier"]))

        ok = process_single_stop(
            gtfs_path=args.gtfs_file,
            stop_id=stop_id,
            stop_name=stop_name,
            output_dir=output_dir,
            style=style,
            tool_dir=tool_dir,
            tier_data=tier_data,
            backdrop_paths=backdrop_paths,
            geographic=do_geographic,
            schematic=do_schematic,
            progressive=args.progressive,
        )

        if ok:
            success_count += 1
            print(f"  Done.", file=sys.stderr)
        else:
            print(f"  Failed.", file=sys.stderr)

    print(f"\nCompleted: {success_count}/{len(stops_to_process)} stops", file=sys.stderr)
    print(f"Output: {output_dir}/", file=sys.stderr)


if __name__ == "__main__":
    main()
