#!/usr/bin/env python3

"""
GTFS Subset CLI - Create filtered subsets of GTFS data with optional map visualization.

Part of the Magga (ಮಗ್ಗ/मग्ग) project: https://github.com/pvnkmrksk/magga
License: GPL-3.0 — see LICENSE file. Author: Pavan Kumar (@pvnkmrksk)
"""

import argparse
from gtfs_analysis import GTFSAnalyzer
from gtfs_map_viewer import GTFSMapCreator
from pathlib import Path
import sys

def create_subset(input_gtfs: str, *, 
                 output: str = None,
                 stops: str = None,
                 routes: str = None,
                 route_ids: str = None,
                 min_trips: int = None,
                 map: bool = False,
                 map_output: str = None,
                 stops_only: bool = False,
                 color_by: str = 'trips',
                 cmap: str = 'magma',
                 route_cmap: str = 'tab20c',
                 **kwargs) -> Path:
    """
    Create a filtered GTFS subset with optional map visualization.

    This function provides a high-level interface for filtering GTFS data based on
    various criteria and optionally generating a visualization of the result.

    Args:
        input_gtfs (str): Path to input GTFS zip file
        output (str, optional): Output path for the filtered GTFS
        stops (str, optional): Comma-separated stop IDs to include
        routes (str, optional): Route patterns to match (supports wildcards)
        route_ids (str, optional): Comma-separated ``route_id`` values (exact)
        min_trips (int, optional): Minimum trips per route
        map (bool, optional): Generate HTML map visualization
        map_output (str, optional): Custom path for map output
        stops_only (bool, optional): Show only stops on map
        color_by (str, optional): Metric for coloring ('trips'/'routes')
        cmap (str, optional): Matplotlib colormap for stops
        route_cmap (str, optional): Matplotlib colormap for routes
        **kwargs: Additional parameters passed to map creation

    Returns:
        Path: Path to the generated GTFS subset

    Example:
        >>> create_subset('input.zip',
        ...              stops='STOP1,STOP2',
        ...              routes='138*',
        ...              min_trips=10,
        ...              map=True)
    """
    # Parse filters
    stop_ids = [s.strip() for s in stops.split(',')] if stops else None
    route_patterns = [r.strip() for r in routes.split(',')] if routes else None
    rid_list = [s.strip() for s in route_ids.split(',')] if route_ids else None
    
    # Generate output name if not provided
    if not output:
        filters = []
        if stop_ids:
            filters.append(f"stops_{'-'.join(stop_ids)}")
        if rid_list:
            filters.append(f"routeids_{'-'.join(rid_list[:4])}{'_etc' if len(rid_list) > 4 else ''}")
        if route_patterns:
            filters.append(f"routes_{'-'.join(route_patterns)}")
        if min_trips:
            filters.append(f"min{min_trips}")
        output = str(Path(input_gtfs).resolve().with_name(
            f"{Path(input_gtfs).stem}_{'_'.join(filters or ['full'])}.zip"
        ))
    
    # Create analyzer instance
    analyzer = GTFSAnalyzer(input_gtfs)
    
    # Create subset (colors will be applied during subsetting)
    subset = analyzer.create_subset(
        output_path=output,
        stop_ids=stop_ids,
        route_patterns=route_patterns,
        route_ids=rid_list,
        min_trips=min_trips
    )
    
    # Print statistics to stderr
    print(f"\nSubset Statistics:", file=sys.stderr)
    print(f"Original routes: {len(analyzer.feed.routes)}", file=sys.stderr)
    print(f"Subset routes: {len(subset.feed.routes)}", file=sys.stderr)
    print(f"Original trips: {len(analyzer.feed.trips)}", file=sys.stderr)
    print(f"Subset trips: {len(subset.feed.trips)}", file=sys.stderr)
    print(f"Original stops: {len(analyzer.feed.stops)}", file=sys.stderr)
    print(f"Subset stops: {len(subset.feed.stops)}", file=sys.stderr)
    
    # Create map if requested
    if map:
        map_path = map_output or str(Path(output).with_suffix('.html'))
        map_creator = GTFSMapCreator(output)
        map_creator.load_gtfs_data()
        map_creator.create_map(
            output_path=map_path,
            stops_only=stops_only,
            color_by=color_by,
            cmap=cmap,
            route_cmap=route_cmap,
            **kwargs
        )
        print(f"Map created at: {map_path}", file=sys.stderr)
    
    # Print the output path to stdout (used by process_transit_map.sh)
    print(output)
    return Path(output)

def main():
    parser = argparse.ArgumentParser(
        description='''
Magga GTFS Subset Generator — Filter GTFS data by stops, routes, or minimum
trip counts. Optionally generate interactive HTML map visualizations.
''',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Input/Output
    parser.add_argument('input_gtfs', 
                       help='Path to input GTFS zip file')
    parser.add_argument('-o', '--output',
                       help='Output path for filtered GTFS (default: auto-generated)')
    
    # Filtering Options
    filter_group = parser.add_argument_group('filtering options')
    filter_group.add_argument('-s', '--stops',
                            help='Comma-separated stop IDs to include')
    filter_group.add_argument('-r', '--routes',
                            help='Route patterns to match (supports wildcards)')
    filter_group.add_argument('--route-ids',
                            help='Comma-separated route_id values (exact GTFS ids)')
    filter_group.add_argument('-m', '--min-trips',
                            type=int,
                            help='Minimum trips per route')
    
    # Visualization Options
    viz_group = parser.add_argument_group('visualization options')
    viz_group.add_argument('--map',
                          action='store_true',
                          help='Generate interactive HTML map')
    viz_group.add_argument('--map-output',
                          help='Custom path for map output (default: input_name.html)')
    viz_group.add_argument('--stops-only',
                          action='store_true',
                          help='Show only stops on map (no routes)')
    viz_group.add_argument('--color-by',
                          choices=['trips', 'routes'],
                          default='trips',
                          help='Metric for coloring stops (default: trips)')
    
    # Style Options
    style_group = parser.add_argument_group('style options')
    style_group.add_argument('--cmap',
                            default='magma',
                            help='Matplotlib colormap for stops (default: magma)')
    style_group.add_argument('--route-cmap',
                            default='tab20c',
                            help='Matplotlib colormap for routes (default: tab20c)')

    parser.epilog = '''
examples:
  # Basic subsetting
  %(prog)s input.zip -o output.zip

  # Filter by stops
  %(prog)s input.zip -s "STOP1,STOP2,STOP3"

  # Filter by routes with wildcards
  %(prog)s input.zip -r "138*,KBS*"

  # Filter by minimum trips
  %(prog)s input.zip -m 10

  # Generate map with custom coloring
  %(prog)s input.zip --map --color-by routes --cmap viridis

  # Complex filtering with visualization
  %(prog)s input.zip -s "STOP1,STOP2" -r "138*" -m 10 --map
  %(prog)s input.zip --route-ids "24o,1jx" -o corridor.zip

notes:
  - Route patterns support wildcards (e.g., "138*" matches "138A", "138B")
  - Generated subsets preserve the organic flow of transit routes
  - Colormaps can be chosen from matplotlib's collection
  - Output includes both data and optional visualization

For more information and documentation:
  https://github.com/pvnkmrksk/magga
'''

    args = parser.parse_args()
    create_subset(**vars(args))

if __name__ == '__main__':
    main()