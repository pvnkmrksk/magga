#!/usr/bin/env python3
"""
Process Doublet Stops - Batch-generate GTFS subsets and maps for stop pairs.

Reads stop pairs from Doublet_stops.csv (columns: stop_name, stop_id_1, stop_id_2).
Part of Magga: https://github.com/pvnkmrksk/magga
"""

import pandas as pd
from pathlib import Path
import subprocess
import os
from gtfs_subset_cli import create_subset

def process_doublet_pair(gtfs_path: str, stop_id_1: str, stop_id_2: str, stop_name: str, output_dir: Path):
    """Process a single pair of doublet stops"""
    # Create a clean name for files
    clean_name = stop_name.replace('/', '_').replace(' ', '_').lower()
    
    # Create subset directory if it doesn't exist
    subset_dir = output_dir / 'subsets'
    subset_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subset GTFS focusing on these two stops
    subset_path = subset_dir / f"{clean_name}.zip"
    create_subset(
        gtfs_path,
        output=str(subset_path),
        stops=f"{stop_id_1},{stop_id_2}",
        stops_only=True
    )
    
    # Generate visualization using gtfs_map_viewer
    subprocess.run(['python', 'gtfs_map_viewer.py', str(subset_path)])

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Process doublet stops from GTFS data')
    parser.add_argument('gtfs_path', help='Path to the input GTFS file')
    parser.add_argument('--output-dir', default='doublet_output',
                      help='Directory to store output files (default: doublet_output)')
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Read doublet stops data
    doublets_df = pd.read_csv('Doublet_stops.csv', index_col=0)
    
    # Process each pair
    for idx, row in doublets_df.iterrows():
        print(f"\nProcessing {row['stop_name']}...")
        try:
            process_doublet_pair(
                args.gtfs_path,
                row['stop_id_1'],
                row['stop_id_2'],
                row['stop_name'],
                output_dir
            )
            print(f"✓ Completed {row['stop_name']}")
        except Exception as e:
            print(f"Error processing {row['stop_name']}: {e}")

if __name__ == '__main__':
    main() 