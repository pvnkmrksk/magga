#!/bin/bash

# Default values for variables
GTFS_FILE="bmtc-2.zip"
CSV_FILE="stop_trip_counts.csv"
OUTPUT_DIR="examples"
MIN_TRIPS=5
OUTPUT_FILE_PREFIX="subset_filtered"
OCTI_ENABLED=false
COLORMAP="tab20c"
IMPORTANT_STOPS=false
HIDE_ROUTES=false
DIRECTION=0
SKIP_DIRECTION=f
# Define the list of stop IDs you want to process
STOP_IDS=("5wx" "32p" "be" "1mm" "2wy")
# Function to display usage
usage() {
    echo "Usage: $0 [-g gtfs_file] [-c csv_file] [-o output_dir] [-m min_trips] [-p output_file_prefix] [-x] [-l colormap] [-i] [-r] [-d direction] [-s]"
    echo "  -g  GTFS file (default: $GTFS_FILE)"
    echo "  -t  Stop IDs (space-separated list, default: ${STOP_IDS[*]})"
    echo "  -c  CSV file (default: $CSV_FILE)"
    echo "  -o  Output directory (default: $OUTPUT_DIR)"
    echo "  -m  Minimum trips (default: $MIN_TRIPS)"
    echo "  -p  Output file prefix (default: $OUTPUT_FILE_PREFIX)"
    echo "  -x  Enable octi (default: disabled)"
    echo "  -l  Colormap name (default: $COLORMAP)"
    echo "  -i  Important stops only (default: disabled)"
    echo "  -r  Hide routes (default: disabled)"
    echo "  -d  Direction (0 for down, 1 for up, default: $DIRECTION)"
    echo "  -s  Skip direction filter (default: disabled)"
    exit 1
}

# Parse command-line arguments
while getopts "g:c:o:m:p:xl:irsd:" opt; do
    case $opt in
        g) GTFS_FILE="$OPTARG" ;;
        t) STOP_IDS="$OPTARG" ;;
        c) CSV_FILE="$OPTARG" ;;
        o) OUTPUT_DIR="$OPTARG" ;;
        m) MIN_TRIPS="$OPTARG" ;;
        p) OUTPUT_FILE_PREFIX="$OPTARG" ;;
        x) OCTI_ENABLED=true ;;
        l) COLORMAP="$OPTARG" ;;
        i) IMPORTANT_STOPS=true ;;
        r) HIDE_ROUTES=true ;;
        d) DIRECTION="$OPTARG" ;;
        s) SKIP_DIRECTION=true ;;
        *) usage ;;
    esac
done

# Check if GTFS file exists
if [ ! -f "$GTFS_FILE" ]; then
    echo "Error: GTFS file '$GTFS_FILE' not found."
    exit 1
fi

# Create the output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"



# Initialize an array to hold stop names
stop_names=()

echo "Starting GTFS processing..."

# Iterate over each stop ID to find corresponding stop names
for stop_id in "${STOP_IDS[@]}"; do
    # Use awk to find the stop_name corresponding to the stop_id
    stop_name=$(awk -F, -v id="$stop_id" '$4 == id {print $2}' "$CSV_FILE")
    
    # Add the stop name to the array if found
    if [ -n "$stop_name" ]; then
        stop_names+=("$stop_name")
        echo "Found stop name for ID $stop_id: $stop_name"
    else
        echo "Warning: Stop ID $stop_id not found in CSV."
    fi
done

# Join all stop names with underscores for the filename
sanitized_stop_names=$(printf "%s_" "${stop_names[@]}" | tr ' ' '_')
sanitized_stop_names=${sanitized_stop_names%_}  # Remove trailing underscore

# Define the output file names (update paths to include output directory)
OUTPUT_FILE="${OUTPUT_DIR}/${OUTPUT_FILE_PREFIX}_all_stops.zip"
FINAL_MAP_FILE="${OUTPUT_DIR}/${OUTPUT_FILE_PREFIX}_${sanitized_stop_names}_map.svg"

echo "Processing GTFS data for stop IDs: ${STOP_IDS[*]}"
echo "Output will be saved to: $FINAL_MAP_FILE"

# Run the GTFS processing for all stop IDs at once, add viz_file name using final_map_file as template
python gtfs_process_cli.py "$GTFS_FILE" "${STOP_IDS[@]}" \
    --output-dir "$OUTPUT_DIR" \
    --min-trips "$MIN_TRIPS" \
    --output "$(basename "$OUTPUT_FILE")" \
    $([ "$IMPORTANT_STOPS" = true ] && echo "--important-stops-only") \
    $([ "$HIDE_ROUTES" = true ] && echo "--hide-routes") \
    --direction "$DIRECTION" \
    $([ "$SKIP_DIRECTION" = true ] && echo "--skip-direction-filter" ) \
    --viz-file "$(basename "$FINAL_MAP_FILE")"

# Check if the GTFS processing was successful
if [ $? -ne 0 ]; then
    echo "Error: GTFS processing failed. Please check the input file and parameters."
    exit 1
fi

# Verify the output file was created (now checking in the correct directory)
if [ ! -f "$OUTPUT_FILE" ]; then
    echo "Error: Output file '$OUTPUT_FILE' was not created."
    exit 1
fi

# Run the subsequent commands
gtfs2graph_cmd="gtfs2graph -m bus $OUTPUT_FILE"
topo_cmd="topo"
color_geojson_cmd="python color_geojson_cli.py -c $COLORMAP"
loom_cmd="loom"
octi_cmd="octi"
transitmap_cmd="transitmap -l > $FINAL_MAP_FILE"

# Chain the commands using pipes
if [ "$OCTI_ENABLED" = true ]; then
    eval "$gtfs2graph_cmd | $topo_cmd | $color_geojson_cmd | $loom_cmd | $octi_cmd | $transitmap_cmd"
else
    eval "$gtfs2graph_cmd | $topo_cmd | $color_geojson_cmd | $loom_cmd | $transitmap_cmd"
fi

# Check if the final map generation was successful
if [ $? -eq 0 ]; then
    echo "Successfully generated map: $FINAL_MAP_FILE"
else
    echo "Error: Map generation failed."x
fi