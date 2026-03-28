#!/bin/bash
# process_gtfs.sh - Parallel batch processing of GTFS files
# Part of Magga: https://github.com/pvnkmrksk/magga

# Show help if no arguments or help flag
if [ $# -eq 0 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Usage: $0 <zip_pattern>"
    echo ""
    echo "Process GTFS zip files matching the given pattern through the map viewer."
    echo "Each file gets an interactive HTML map generated via gtfs_map_viewer.py."
    echo ""
    echo "Requires: GNU parallel (apt install parallel)"
    echo ""
    echo "Examples:"
    echo "  $0 'stop_analysis/subsets/*.zip'"
    echo "  $0 'data/*.zip'"
    exit 0
fi

# Get total count of files to process
total=$(find $1 -type f | wc -l)
echo "Processing $total GTFS files..."

# Process files with simplified progress output
find $1 -type f | \
parallel --joblog process_log.txt \
    'echo "Processing {/.} ($PARALLEL_SEQ of '$total')" && \
     python gtfs_map_viewer.py {} && \
     echo "✓ Completed {/.}"' 