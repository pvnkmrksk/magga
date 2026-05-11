#!/bin/bash
# process_doublets.sh - Process GTFS data for doublet stop pairs
# Part of Magga: https://github.com/pvnkmrksk/magga

if [ $# -eq 0 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
    echo "Usage: $0 <gtfs_file>"
    echo ""
    echo "Process GTFS file for each doublet stop pair from Doublet_stops.csv."
    echo "Generates transit maps for each pair using process_transit_map.sh."
    echo ""
    echo "Expects Doublet_stops.csv in current directory with columns:"
    echo "  index, stop_name, stop_id_1, stop_id_2, ..."
    echo ""
    echo "Config (edit in script):"
    echo "  START_ROW  — skip to this row number (default: 30)"
    echo "  OUTPUT_DIR — output directory (default: doublet_output)"
    exit 0
fi

GTFS_FILE=$1
OUTPUT_DIR="doublet_output"
START_ROW=30

mkdir -p "$OUTPUT_DIR"

# Skip to row 30 and process one at a time
row_num=1
while IFS=, read -r _ name id1 id2 _; do
    if [ $row_num -lt $START_ROW ]; then
        row_num=$((row_num + 1))
        continue
    fi
    
    # Clean the name and IDs
    clean_name=$(echo "$name" | tr -d '"' | tr ' /' '_' | tr -d '()')
    id1=$(echo "$id1" | tr -d ' ')
    id2=$(echo "$id2" | tr -d ' ')
    
    echo "Processing $clean_name (stops: $id1,$id2)..."
    
    # Create directory and run transit map
    pair_dir="$OUTPUT_DIR/$clean_name"
    mkdir -p "$pair_dir"
    ./process_transit_map.sh "$GTFS_FILE" --stops "$id1,$id2" --output-dir "$pair_dir" --min-trips 15
    
    row_num=$((row_num + 1))
done < <(tail -n +2 Doublet_stops.csv) 