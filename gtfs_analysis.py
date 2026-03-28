#!/usr/bin/env python3

"""
GTFS Analysis - Analyze, filter, and subset GTFS transit data.

Part of the Magga (ಮಗ್ಗ/मग्ग) project: https://github.com/pvnkmrksk/magga
License: GPL-3.0 — see LICENSE file. Author: Pavan Kumar (@pvnkmrksk)
"""

import partridge as ptg
import pandas as pd
from typing import List, Set, Dict, Union
from pathlib import Path
import natsort
import sys

class GTFSAnalyzer:
    """
    A comprehensive analyzer for GTFS transit data.
    
    This class provides functionality for analyzing GTFS feeds, including:
    - Computing various metrics about stops and routes
    - Creating filtered subsets of GTFS data
    - Applying consistent route coloring
    
    The analyzer supports various filtering criteria such as:
    - Minimum trip counts per route
    - Specific stops or routes
    - Pattern matching for route names
    
    Attributes:
        feed_path (str): Path to the GTFS feed file
        feed (partridge.Feed): Loaded GTFS feed object
    
    Example:
        >>> analyzer = GTFSAnalyzer("input.zip")
        >>> metrics = analyzer.analyze_stop_metrics()
        >>> subset = analyzer.create_subset(
        ...     "output.zip",
        ...     stop_ids=["STOP1", "STOP2"],
        ...     min_trips=10
        ... )
    """
    
    def __init__(self, feed_path: Union[str, Path]):
        """Initialize with a GTFS feed path"""
        self.feed_path = str(feed_path)
        self.feed = ptg.load_feed(self.feed_path)
        
    def analyze_stop_metrics(self, output_dir: str = "analysis") -> Dict[str, pd.DataFrame]:
        """
        Analyze stops based on different metrics:
        1. Stops with most trips
        2. Stops with most unique routes
        3. Routes with most trips
        
        Returns dictionary containing all analysis dataframes
        """
        # Create output directory if it doesn't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        results = {
            'stops_by_trips': (
                self.feed.stop_times
                .groupby('stop_id')['trip_id']
                .nunique()
                .reset_index(name='trip_count')
                .merge(self.feed.stops[['stop_id', 'stop_name']], on='stop_id')
                .sort_values('trip_count', ascending=False)
            ),
            'stops_by_routes': (
                self.feed.stop_times
                .merge(self.feed.trips[['trip_id', 'route_id']], on='trip_id')
                .groupby('stop_id')['route_id']
                .nunique()
                .reset_index(name='route_count')
                .merge(self.feed.stops[['stop_id', 'stop_name']], on='stop_id')
                .sort_values('route_count', ascending=False)
            ),
            'routes_by_trips': (
                self.feed.trips
                .groupby('route_id')
                .size()
                .reset_index(name='trip_count')
                .merge(
                    self.feed.routes[['route_id', 'route_short_name', 'route_long_name']], 
                    on='route_id'
                )
                .sort_values('trip_count', ascending=False)
            )
        }
        
        # Save results to CSV
        for name, df in results.items():
            df.to_csv(f"{output_dir}/{name}.csv", index=False)
            
        return results

    def subset_by_min_trips(self, min_trips: int) -> Set[str]:
        """Get trips from routes that have at least min_trips trips"""
        route_trip_counts = self.feed.trips.groupby('route_id').size()
        qualifying_routes = route_trip_counts[route_trip_counts >= min_trips].index
        
        return set(
            self.feed.trips[
                self.feed.trips['route_id'].isin(qualifying_routes)
            ]['trip_id']
        )

    def create_subset(self, 
                     output_path: str,
                     stop_ids: List[str] = None,
                     route_patterns: List[str] = None,
                     min_trips: int = None) -> 'GTFSAnalyzer':
        """
        Create a GTFS subset by chaining multiple filters.
        Returns a new GTFSAnalyzer instance with the subset feed.
        
        Parameters:
        -----------
        output_path : str
            Path where the subset GTFS will be saved
        stop_ids : List[str], optional
            List of stop IDs to include. All routes serving these stops will be included.
        route_patterns : List[str], optional
            List of route patterns (supports wildcards like "138*"). Only stops served by 
            these routes will be included.
        min_trips : int, optional
            Minimum number of trips a route must have to be included
        """
        qualifying_trips = set()
        stops_to_keep = set()
        
        # First handle route patterns if specified
        if route_patterns and len(route_patterns) > 0:
            for pattern in route_patterns:
                if '*' in pattern:
                    # Wildcard pattern, use regex match
                    matching_routes = self.feed.routes[
                        self.feed.routes['route_short_name'].str.match(
                            pattern.replace('*', '.*'),
                            na=False
                        )
                    ]['route_id']
                else:
                    # Exact match
                    matching_routes = self.feed.routes[
                        self.feed.routes['route_short_name'].str.fullmatch(pattern, na=False)
                    ]['route_id']
                qualifying_trips.update(
                    self.feed.trips[
                        self.feed.trips['route_id'].isin(matching_routes)
                    ]['trip_id']
                )

            # If only routes specified, get only stops served by these routes
            if not stop_ids:
                stops_to_keep.update(
                    self.feed.stop_times[
                        self.feed.stop_times['trip_id'].isin(qualifying_trips)
                    ]['stop_id']
                )
        
        # Then handle stops if specified
        if stop_ids and len(stop_ids) > 0:
            # Get all trips that serve these stops
            stop_trips = set(
                self.feed.stop_times[
                    self.feed.stop_times['stop_id'].isin(stop_ids)
                ]['trip_id']
            )
            qualifying_trips.update(stop_trips)
            
            # Get all stops served by these trips (not just the specified stops)
            stops_to_keep.update(
                self.feed.stop_times[
                    self.feed.stop_times['trip_id'].isin(stop_trips)
                ]['stop_id']
            )
        
        # If neither stops nor routes specified, use all trips and stops
        if not qualifying_trips:
            qualifying_trips = set(self.feed.trips['trip_id'])
            stops_to_keep = set(self.feed.stops['stop_id'])
        
        # Apply minimum trips filter if specified
        if min_trips:
            qualifying_trips &= self.subset_by_min_trips(min_trips)
            
        # Get routes to keep
        routes_to_keep = set(self.feed.trips[
            self.feed.trips['trip_id'].isin(qualifying_trips)
        ]['route_id'])
        
        # Create a temporary directory for the new feed
        import tempfile
        import shutil
        import os
        from zipfile import ZipFile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Extract the original feed
            with ZipFile(self.feed_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            # Save the filtered routes with colors
            filtered_routes = self.feed.routes[
                self.feed.routes['route_id'].isin(routes_to_keep)
            ].copy()
            color_mapping = self.apply_route_colors_to_df(filtered_routes)
            filtered_routes.to_csv(os.path.join(tmpdir, 'routes.txt'), index=False)
            
            # Create the view spec for other files
            view = {
                'trips.txt': {'trip_id': list(qualifying_trips)},
                'stops.txt': {'stop_id': list(stops_to_keep)} if stops_to_keep else None
            }
            
            # Filter out None values from view
            view = {k: v for k, v in view.items() if v is not None}
            
            # Create temporary subset
            temp_output = os.path.join(tmpdir, 'temp_subset.zip')
            ptg.extract_feed(
                self.feed_path,
                temp_output,
                view
            )
            
            # Extract the temporary subset
            subset_dir = os.path.join(tmpdir, 'subset')
            os.makedirs(subset_dir, exist_ok=True)
            with ZipFile(temp_output, 'r') as zip_ref:
                zip_ref.extractall(subset_dir)
            
            # Copy our modified routes.txt to the subset
            shutil.copy(
                os.path.join(tmpdir, 'routes.txt'),
                os.path.join(subset_dir, 'routes.txt')
            )
            
            # Create the final zip with all files including modified routes.txt
            with ZipFile(output_path, 'w') as zip_ref:
                for root, _, files in os.walk(subset_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, subset_dir)
                        zip_ref.write(file_path, arcname)
        
        return GTFSAnalyzer(output_path)

    def apply_route_colors_to_df(self, routes_df: pd.DataFrame, cmap: str = 'tab20c') -> Dict[str, str]:
        """
        Generate and apply colors to a routes DataFrame using a matplotlib colormap.
        Routes are naturally sorted by route_short_name before color assignment.
        Colors are stored without the '#' prefix and in uppercase.
        """
        import matplotlib.pyplot as plt
        import numpy as np
        
        # Get route names and IDs as numpy arrays
        route_names = routes_df['route_short_name'].fillna('').to_numpy()
        route_ids = routes_df['route_id'].to_numpy()
        
        # Create sorted indices using natsort
        sorted_idx = np.array(natsort.index_natsorted(route_names))
        
        # Apply sorting to both arrays at once
        route_ids = route_ids[sorted_idx]
        
        # Generate colors vectorized
        colormap = plt.get_cmap(cmap)
        colors_rgba = colormap(np.linspace(0, 1, len(route_ids)))
        
        # Convert to hex colors using numpy operations
        colors_rgb = (colors_rgba[:, :3] * 255).astype(np.uint8)
        hex_colors = np.apply_along_axis(
            lambda x: f'{x[0]:02X}{x[1]:02X}{x[2]:02X}', 1, colors_rgb  # Note: uppercase hex without #
        )
        
        # Create the mapping
        color_mapping = dict(zip(route_ids, hex_colors))
        
        # Update the routes DataFrame with new colors
        routes_df['route_color'] = (
            routes_df['route_id']
            .map(color_mapping)
            .fillna('')
            .astype(str)  # Convert to string type
        )
        routes_df['route_text_color'] = 'FFFFFF'  # White text for contrast
        
        print(f"Successfully set colors for {routes_df['route_color'].ne('').sum()} routes", file=sys.stderr)
        
        return color_mapping