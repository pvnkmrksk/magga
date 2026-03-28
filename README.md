# Magga (ಮಗ್ಗ/मग्ग)

[![Build](https://github.com/pvnkmrksk/magga/actions/workflows/build.yml/badge.svg)](https://github.com/pvnkmrksk/magga/actions/workflows/build.yml)

A toolkit for weaving transit data into beautiful, meaningful maps.

"Magga" carries dual meaning — a loom (ಮಗ್ಗ) in Kannada that weaves intricate patterns, and "path" (मग्ग) in Pali, referring to the noble path toward enlightenment. We weave transit routes into readable maps, illuminating paths toward sustainable and equitable mobility.

## Quick Reference

```bash
# End-to-end: GTFS zip → geographic + schematic SVG maps
./process_transit_map.sh data.zip

# Filter to specific stops and routes
./process_transit_map.sh data.zip -s "STOP1,STOP2" -r "138*" -m 10

# Interactive HTML map of a GTFS file
python gtfs_map_viewer.py data.zip -o map.html

# Create a filtered GTFS subset
python gtfs_subset_cli.py data.zip -s "STOP1,STOP2" -m 15 -o subset.zip

# Create subset + generate interactive map in one step
python gtfs_subset_cli.py data.zip -r "138*" -m 10 --map

# Manual pipeline: GTFS → graph → topo → loom → schematic SVG
gtfs2graph -m bus subset.zip | topo --smooth 20 -d 150 | loom | octi | transitmap -l > map.svg

# Geographic map (skip octi for non-schematic layout)
gtfs2graph -m bus subset.zip | topo --smooth 20 -d 150 | loom | transitmap -l > geo.svg

# Shrink text in a generated SVG to 85% size
python adjust_svg.py input.svg output.svg 0.85

# Generate maps for top 10 stops with progressive hiding + backdrop
python generate_all_stops.py data.zip -n 10 --progressive --backdrop

# Generate maps for specific stops, geographic only
python generate_all_stops.py data.zip --stops "STOP1,STOP2" --geographic-only

# Save default style config for customization
python generate_all_stops.py data.zip -n 1 --save-style -o output/
# Then edit output/_style.json and re-run with: --style output/_style.json
```

## Installation

### C++ Pipeline Tools

```bash
git clone --recurse-submodules https://github.com/pvnkmrksk/magga.git
cd magga
mkdir build && cd build
cmake ..
make -j
```

If you already cloned without `--recurse-submodules`:
```bash
git submodule update --init --recursive
```

Optionally install system-wide:
```bash
sudo make install
```

### Python Dependencies

```bash
pip install -r requirements.txt
```

Required packages: pandas, partridge, folium, branca, matplotlib, numpy, natsort, tqdm.

### GTFS Data

You need GTFS (General Transit Feed Specification) zip files as input. Download them from:
- [Transitland](https://www.transit.land/feeds)
- [OpenMobilityData](https://openmobilitydata.org/)
- Your local transit agency's open data portal

## Tools

### process_transit_map.sh — Full Pipeline

Automates the entire flow: GTFS filtering → graph conversion → layout → SVG rendering → text adjustment.

```
Usage: ./process_transit_map.sh <gtfs_file> [options]

Data Filtering:
  -s, --stops <ids>           Comma-separated stop IDs to include
  -r, --routes <patterns>     Route patterns (supports wildcards, e.g. "138*")
  -m, --min-trips <num>       Minimum trips per route (default: 15)
  -d, --max-dist <meters>     Max aggregation distance (default: 150)
  -sm, --smooth <value>       Smoothing factor (default: 20)

Visual Styling:
  -w, --line-width <px>       Line width (default: 20)
  -sp, --line-spacing <px>    Space between parallel lines (default: 10)
  -sl, --station-label-size   Station label text size (default: 60)
  -ll, --line-label-size      Line label text size (default: 40)
  -ts, --text-shrink <ratio>  Text shrink ratio 0-1 (default: 0.85)

Output:
  -o, --output-dir <path>     Output directory (default: output)
  -v, --verbose               Enable detailed logging
```

**Examples:**
```bash
# Basic — all routes with ≥15 trips
./process_transit_map.sh city_transit.zip

# Specific stops, custom styling
./process_transit_map.sh city_transit.zip -s "STOP1,STOP2" -w 25 -sl 70

# Wildcard route filtering with lower trip threshold
./process_transit_map.sh city_transit.zip -r "138*,KBS*" -m 5 -o maps/
```

**Output:**
```
output/
├── <name>.zip                    # Filtered GTFS subset
├── <name>_loom.json              # Intermediate graph data
├── <name>_geographic.svg         # Geographic layout map
└── <name>_schematic.svg          # Schematic (octilinear) map
```

### generate_all_stops.py — Batch Per-Stop Map Generation

Generate geographic and/or schematic SVGs for every stop (or top N) with:
- Semantic SVG layers (Inkscape-compatible: Routes, Stations, Labels by tier)
- Progressive label hiding variants (full / important / junctions / minimal)
- Optional HF corridor backdrop for city-wide context
- Configurable style via JSON

```
Usage: python generate_all_stops.py <gtfs_file> [options]

  -o, --output-dir <path>      Output directory (default: stop_maps)
  -n, --top-n <num>            Only top N stops by importance
  --stops <ids>                Specific stop IDs to process
  -m, --min-trips <num>        Min trips for route inclusion (default: 5)
  --backdrop                   Include HF corridor backdrop layer
  --progressive                Generate progressive hiding variants
  --geographic-only            Skip schematic maps
  --schematic-only             Skip geographic maps
  --style <json>               Style config file
  --save-style                 Save effective style to output dir
```

**Examples:**
```bash
# Top 5 stops with all features
python generate_all_stops.py city.zip -n 5 --progressive --backdrop

# Specific stops, geographic only, custom style
python generate_all_stops.py city.zip --stops "MAIN,CENTRAL" --geographic-only --style style.json
```

**Output structure:**
```
stop_maps/
├── _style.json                    # Style config used
├── _stop_importance.csv           # All stops ranked by importance
├── _hf_corridor_geographic.svg    # Shared HF backdrop (if --backdrop)
├── STOP1_name/
│   ├── geographic.svg             # Full labels, layered
│   ├── geographic_important.svg   # Only important stop labels
│   ├── geographic_junctions.svg   # Only junction labels
│   ├── geographic_minimal.svg     # No labels
│   ├── geographic_with_backdrop.svg
│   ├── schematic.svg
│   ├── schematic_*.svg            # Same variants
│   ├── stop_info.json             # Metadata
│   └── subset.zip                 # GTFS subset used
```

### gtfs_subset_cli.py — GTFS Filtering

Create filtered subsets of GTFS data, optionally with an interactive HTML map.

```
Usage: python gtfs_subset_cli.py <input.zip> [options]

  -o, --output <path>         Output GTFS path (auto-generated if omitted)
  -s, --stops <ids>           Comma-separated stop IDs
  -r, --routes <patterns>     Route patterns (wildcards supported)
  -m, --min-trips <num>       Minimum trips per route
  --map                       Generate interactive HTML map
  --map-output <path>         Custom map output path
  --color-by {trips,routes}   Metric for coloring stops (default: trips)
  --cmap <name>               Matplotlib colormap for stops (default: magma)
  --route-cmap <name>         Matplotlib colormap for routes (default: tab20c)
```

**Examples:**
```bash
# Filter to stops and generate a map
python gtfs_subset_cli.py city.zip -s "MAIN_ST,CENTRAL" --map

# Routes matching a pattern, min 10 trips
python gtfs_subset_cli.py city.zip -r "138*,KBS*" -m 10 -o filtered.zip

# Custom visualization
python gtfs_subset_cli.py city.zip --map --color-by routes --cmap viridis
```

### gtfs_map_viewer.py — Interactive HTML Maps

Generates an interactive web map from a GTFS file with routes and stops.

```
Usage: python gtfs_map_viewer.py <input.zip> [options]

  -o, --output <path>         Output HTML path (default: transit_map.html)
  --stops-only                Show only stops, hide routes
  --color-by {trips,routes}   Metric for coloring stops (default: trips)
  --cmap <name>               Colormap for stops (default: magma)
  --route-cmap <name>         Colormap for routes (default: magma)
```

**Examples:**
```bash
python gtfs_map_viewer.py city.zip -o city_map.html
python gtfs_map_viewer.py city.zip --color-by routes --cmap YlOrRd
python gtfs_map_viewer.py city.zip --stops-only --cmap viridis
```

### adjust_svg.py — SVG Text Adjustment

Scales text sizes in generated SVG maps for better readability.

```
Usage: python adjust_svg.py <input_svg> <output_svg> <scale_factor>

  scale_factor: e.g. 0.85 to shrink text to 85%, 1.2 to enlarge to 120%
```

### Manual Pipeline

For fine-grained control, run the C++ tools individually:

```bash
# 1. Convert GTFS to graph
gtfs2graph -m bus subset.zip > graph.json

# 2. Handle overlapping edges, cluster nearby stations
topo --smooth 20 -d 150 < graph.json > topo.json

# 3. Optimize line arrangements
loom < topo.json > loom.json

# 4a. Schematic map (octilinear layout)
octi < loom.json | transitmap -l --tight-stations --render-dir-markers > schematic.svg

# 4b. Geographic map (skip octi)
transitmap -l --tight-stations --render-dir-markers < loom.json > geographic.svg
```

## Helper Scripts

These are batch-processing utilities for specific workflows:

| Script | Purpose | Requires |
|--------|---------|----------|
| `process_gtfs.sh` | Process multiple GTFS files in parallel | GNU `parallel` |
| `process_doublets.sh` | Process doublet stop pairs from CSV | `Doublet_stops.csv` |
| `process_doublet_stops.py` | Python version of doublet processing | `Doublet_stops.csv` |
| `process_top_stops.py` | Batch analysis of top stops (**experimental**, has known issues) | Hardcoded paths |

```bash
# Parallel processing of multiple GTFS files
./process_gtfs.sh 'stop_analysis/subsets/*.zip'

# Process doublet stop pairs
./process_doublets.sh city_transit.zip
```

## Project Structure

```
magga/
├── process_transit_map.sh      # Main pipeline script
├── gtfs_subset_cli.py          # GTFS filtering CLI
├── generate_all_stops.py        # Batch per-stop map generation
├── magga_style.py              # Style configuration (colormaps, fonts, tiers)
├── stop_importance.py          # Stop scoring & distance computation
├── svg_layers.py               # SVG layer post-processor
├── gtfs_map_viewer.py          # Interactive HTML map generator
├── gtfs_analysis.py            # GTFS analysis library
├── adjust_svg.py               # SVG text size adjuster
├── requirements.txt            # Python dependencies
├── src/                        # C++ source code
│   ├── gtfs2graph/             #   GTFS → graph converter
│   ├── topo/                   #   Topology handler (edge overlap, clustering)
│   ├── loom/                   #   Line arrangement optimizer
│   ├── octi/                   #   Octilinear (schematic) layout
│   ├── transitmap/             #   SVG renderer with labels
│   ├── shared/                 #   Shared utilities
│   ├── cppgtfs/                #   GTFS C++ library (submodule)
│   └── util/                   #   Utility library (submodule)
├── examples/                   # Sample data and rendered maps
├── Dockerfile                  # Docker build with Gurobi support
└── CMakeLists.txt              # C++ build configuration
```

## Requirements

**C++ build:**
- cmake (3.10+)
- gcc >= 5.0 or clang >= 3.9
- Optional: libglpk-dev, coinor-libcbc-dev, gurobi, libzip-dev, libprotobuf-dev

**Python tools:**
- Python 3.6+
- Packages listed in `requirements.txt`

**Helper scripts:**
- GNU `parallel` (for `process_gtfs.sh`)

## Docker

```bash
docker build -t magga .
docker run -i magga gtfs2graph -m bus < input.zip

# With Gurobi license for advanced optimization
docker run -v /path/to/gurobi.lic:/gurobi/gurobi.lic magga <TOOL>
```

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE) for details.

This work builds upon the LOOM project by Hannah Bast, Patrick Brosi, and Sabine Storandt:
- [Efficient Generation of Geographically Accurate Transit Maps](http://ad-publications.informatik.uni-freiburg.de/SIGSPATIAL_transitmaps_2018.pdf) (SIGSPATIAL 2018)
- [Metro Maps on Octilinear Grid Graphs](http://ad-publications.informatik.uni-freiburg.de/EuroVis%20octi-maps.pdf) (EuroVis 2020)
- [Metro Maps on Flexible Base Grids](http://ad-publications.informatik.uni-freiburg.de/SSTD_Metro%20Maps%20on%20Flexible%20Base%20Grids.pdf) (SSTD 2021)

## Author

ಪವನ ಕುಮಾರ | Pavan Kumar, PhD
[@pvnkmrksk](https://github.com/pvnkmrksk)

## TODO

### Name Processing
- [ ] Procedural name shortening (Street → St, Road → Rd) with multilingual support

### Stop Consolidation
- [ ] Lat-long based stop merging within configurable distance threshold

### Subsetting Features
- [ ] Distance-based network subsetting (radius from focus stops)

### Route Filtering
- [ ] Pattern-based route exclusion (glob/regex blacklist)

### Major Junction Handling
- [ ] Junction detection based on route intersection count / passenger volume
- [ ] Smart label placement and density control for junctions
