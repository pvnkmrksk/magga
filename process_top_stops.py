"""
Process Top Stops - Batch analysis of highest-traffic stops (EXPERIMENTAL).

NOTE: This script has known issues:
  - Calls analyzer.subset_by_stops() which does not exist on GTFSAnalyzer.
    The correct method is analyzer.create_subset(stop_ids=[...], output_path=...).
  - Hardcoded input path 'bmtc-2.zip' — edit INPUT_GTFS before use.

Part of Magga: https://github.com/pvnkmrksk/magga
"""

import pandas as pd
from gtfs_analysis import GTFSAnalyzer
from pathlib import Path
import os
from tqdm import tqdm

def main():
    # Configuration
    INPUT_GTFS = "bmtc-2.zip"
    OUTPUT_BASE = "stop_analysis"
    
    # Create output directories
    Path(os.path.join(OUTPUT_BASE, "subsets")).mkdir(parents=True, exist_ok=True)
    Path(os.path.join(OUTPUT_BASE, "analysis")).mkdir(parents=True, exist_ok=True)
    
    # Get top 1000 stops
    print("Analyzing main GTFS feed...")
    analyzer = GTFSAnalyzer(INPUT_GTFS)
    results = analyzer.analyze_stop_metrics()
    top_stops = results['stops_by_trips'].iloc[:]
    
    # Save stops list
    top_stops[['stop_id', 'stop_name', 'trip_count']].to_csv(
        os.path.join(OUTPUT_BASE, "stops_summary.csv"), 
        index=False
    )
    
    # Process each stop
    print("\nProcessing stops...")
    for _, row in tqdm(top_stops.iterrows(), total=len(top_stops), desc="Processing stops"):
        stop_id = row['stop_id']
        stop_name = row['stop_name']
        
        # Clean name for filename
        clean_name = "".join(c if c.isalnum() else "_" for c in stop_name)
        output_name = f"{stop_id}_{clean_name[:50]}"
        
        subset_path = os.path.join(OUTPUT_BASE, "subsets", f"{output_name}.zip")
        analysis_path = os.path.join(OUTPUT_BASE, "analysis", f"{output_name}.csv")
        
        # Skip if already processed
        if os.path.exists(subset_path) and os.path.exists(analysis_path):
            continue
            
        try:
            # Create subset
            subset_feed = analyzer.subset_by_stops(
                stop_ids=[stop_id],
                output_path=subset_path
            )
            
            # Analyze routes through this stop
            subset_analyzer = GTFSAnalyzer(subset_path)
            stop_results = subset_analyzer.analyze_stop_metrics()
            
            # Save top 30 routes summary
            routes_summary = stop_results['routes_by_trips']
            routes_summary.to_csv(analysis_path, index=False)
            
        except Exception as e:
            print(f"\nError processing stop {stop_id} ({stop_name}): {str(e)}")
            continue

    print("\nProcessing complete!")

if __name__ == "__main__":
    main()