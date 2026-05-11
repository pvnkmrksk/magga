# Magga (ಮಗ್ಗ/मग्ग)

[![Build](https://github.com/pvnkmrksk/magga/actions/workflows/build.yml/badge.svg)](https://github.com/pvnkmrksk/magga/actions/workflows/build.yml)

A toolkit for weaving transit data into beautiful, meaningful maps.

"Magga" carries dual meaning — a loom (ಮಗ್ಗ) in Kannada that weaves intricate patterns, and "path" (मग्ग) in Pali, referring to the noble path toward enlightenment. We weave transit routes into readable maps, illuminating paths toward sustainable and equitable mobility.

## Example maps (BMTC — Mathikere)

**Geographic** maps follow the street graph; **schematic** maps use an octilinear layout. These screenshots were built with **large station and route label sizes** (`process_transit_map.sh` `-sl` / `-ll`, `-ts 1.0`) so stop names and line numbers stay readable at README scale. The images use **HTML `<img>` tags** with `https://raw.githubusercontent.com/...` URLs so they show **inline in Cursor/VS Code Markdown preview** (the preview webview often fails to load plain `![](relative.png)` paths). Source PNGs live in [`examples/readme/`](examples/readme/).

### Mathikere Post Office (small neighborhood subset)

Geographic:

<p align="center"><img src="https://raw.githubusercontent.com/pvnkmrksk/magga/master/examples/readme/mathikere_post_office_geographic.png" alt="Mathikere Post Office — geographic transit map" width="920"></p>

Schematic:

<p align="center"><img src="https://raw.githubusercontent.com/pvnkmrksk/magga/master/examples/readme/mathikere_post_office_schematic.png" alt="Mathikere Post Office — schematic octilinear map" width="920"></p>

### S R S Mathikere corridor (paired-stop batch)

Geographic:

<p align="center"><img src="https://raw.githubusercontent.com/pvnkmrksk/magga/master/examples/readme/srs_mathikere_corridor_geographic.png" alt="S R S Mathikere corridor — geographic map" width="920"></p>

Schematic:

<p align="center"><img src="https://raw.githubusercontent.com/pvnkmrksk/magga/master/examples/readme/srs_mathikere_corridor_schematic.png" alt="S R S Mathikere corridor — schematic map" width="920"></p>

## Command layers

Work from the top when you can; drop down only when you need a narrow knob or a debugger’s view.

| Layer | Tool | Role |
|-------|------|------|
| **1** | `magga_cli.py` | **One-stop shop:** stop/route rankings (CSV), top-*N* or top-*%* route subsets, trip-frequency plot. Built on `network_stats` + `GTFSAnalyzer`. |
| **2** | `process_transit_map.sh` | **SVG transit maps (primary output):** optional filter (`-s`, `-r`, `-m`, **`--route-ids`**, **`--top-routes` / `-n`**) → C++ pipeline → geographic + schematic SVG + Indic font fix. |
| **3** | Focused Python CLIs | **Specialist / debugging:** subset-only, stats-only, Folium HTML, `batch_transit_maps.py` (EN/KN × merged stops × route families), per-stop batches, translation helpers. |
| **4** | C++ tools (`gtfs2graph` …) | **Full control** over each pipeline stage. |

**Typical end-to-end (rank → subset → map):**

```bash
# 1) Stats + plot + top-50 routes subset (Layer 1)
python magga_cli.py city.zip \
  --stats-dir output/network_stats \
  --plot-top-routes 50 --plot-output output/routes_top50.png \
  --subset-top-routes 50 --subset-output output/top50.zip --subset-min-trips 1

# 2) Geographic + schematic SVGs from that subset (Layer 2)
./process_transit_map.sh output/top50.zip -m 1 -lt 600 -o output/maps_top50

# Or skip the intermediate zip: top 50 routes by trips, straight to SVG (same pipeline)
./process_transit_map.sh city.zip -n 50 -m 1 -lt 600 -o output/maps_top50_direct
```

**Other Layer 1 examples:**

```bash
# Top 10% of routes by scheduled trip count (HFR-style cut)
python magga_cli.py city.zip \
  --subset-top-routes-pct 10 --subset-output output/top10pct.zip --subset-min-trips 1

# Stats + chart only (no new zip)
python magga_cli.py city.zip --stats-dir output/stats --plot-top-routes 50
```

**Layer 2 shortcuts:**

```bash
./process_transit_map.sh data.zip
./process_transit_map.sh data.zip -s "STOP1,STOP2" -r "138*" -m 10 -lt 600 -o maps/
# Top 100 routes (English labels) vs Kannada stop names: run twice on en vs kn GTFS zips
./process_transit_map.sh city.zip -n 100 -m 1 -lt 600 -o output/svg_top100_en
./process_transit_map.sh city-kn.zip -n 100 -m 1 -lt 600 -o output/svg_top100_kn
```

Use `export MAGGA_PYTHON=/path/to/venv/bin/python` if `python3` lacks `partridge`. See `process_transit_map.sh -h` for `-lt` (loom time limit) and styling flags.

**Batch orchestration (`batch_transit_maps.py`):** merged same-name stops (rare-first), least-first single stops, route wildcards (`413*`) or regex on `route_short_name` (`^31[0-9]`), EN+KN feeds, `default`/`compact` style profiles. Progressive SVG variants (`*_important.svg`, `*_junctions.svg`, `*_minimal.svg` = reduced labels) come from `generate_all_stops.py --progressive`.

```bash
# Test (1 merged name-group + top-3 route SVGs)
python batch_transit_maps.py demo --en-feed city.zip --out output/batch_smoke

# Rarest 50 merged names, EN + KN (KN pass applies Indic font fix)
python batch_transit_maps.py stops --en-feed city.zip --kn-feed city-kn.zip --out output/batch \\
  --merge-names --max-groups 50 --profiles default compact --skip-existing

# Then 100 merged groups (new folder: change --max-groups 100 or copy output tree)

# Rarest 100 individual stops (no name merge)
python batch_transit_maps.py stops --en-feed city.zip --out output/batch --least-first --max-groups 100

# Route families
python batch_transit_maps.py routes --en-feed city.zip --out output/batch \\
  --wildcard '413*' --regex '^31[0-9]'
```

**Tests:**

```bash
pip install -r requirements.txt   # includes pytest
python -m pytest tests/ -q
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

If the C++ build fails because `Min`/`Max` macros in `src/util` clash with your platform headers, apply the bundled patch once (from the repo root):

```bash
patch -p1 -d src/util < patches/util-rtree-minmax.patch
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

Required packages: pandas, partridge, folium, branca, matplotlib, plotly, numpy, natsort, tqdm, pytest (for `tests/`).

### GTFS Data

You need GTFS (General Transit Feed Specification) zip files as input. Download them from:
- [Transitland](https://www.transit.land/feeds)
- [OpenMobilityData](https://openmobilitydata.org/)
- Your local transit agency's open data portal

## Tools

The sections below are **Layer 2–3** references: use them when you need one tool in isolation, exact flags, or to debug. For the usual “analyze network → subset → map” flow, start with [**Command layers**](#command-layers) and `magga_cli.py`.

### magga_cli.py — Unified stats, plots, and route subsets (Layer 1)

Wraps `network_stats` and `GTFSAnalyzer.create_subset` (including exact `route_id` lists for top-*N* / top-*%* routes).

```bash
python magga_cli.py --help
python magga_cli.py city.zip --stats-dir stats --plot-top-routes 50 \
  --subset-top-routes 50 --subset-output top50.zip --subset-min-trips 1

# Interactive HTML + matching matplotlib PNG (…_static.png next to the HTML by default)
python magga_cli.py city.zip --plotly-html output/routes_plotly.html --plotly-top-routes 100

# Kannada (or other) route names on bar charts: JSON next to the zip, or --route-labels-json PATH
# File shape: {"<route_id>": "ಕನ್ನಡ ಹೆಸರು"} or {"<route_id>": {"kn": "…", "en": "…"}}
python magga_cli.py city.zip --plotly-html out/r.html --kannada
python magga_cli.py city.zip --plot-top-routes 50 --kannada

# Interactive map: top 100 routes; route + stop popups = GTFS (English) + Kannada when JSON exists
#   <zip_stem>_route_labels_kn.json  (route_id keys)  and/or  <zip_stem>_stop_labels_kn.json  (stop_id keys)
python magga_cli.py city.zip --map-html out/top100.html --map-top-routes 100 --kannada

# One pass — stats CSVs, Plotly + static PNG, top-100 bar chart, bilingual Folium map (same JSON files as above)
python magga_cli.py city.zip --kannada \
  --stats-dir output/network_stats \
  --plotly-html output/network_stats/routes_trip_plotly.html \
  --plot-top-routes 100 --plot-output output/network_stats/top100_routes.png \
  --map-html output/network_stats/top100_routes_map.html --map-top-routes 100
```

### export_gtfs_network_stats.py — CSV-only network tables (Layer 3)

Same ranking CSVs as `magga_cli.py --stats-dir`, without plots or subsets. Useful in scripts.

```bash
python export_gtfs_network_stats.py city.zip -o output/network_stats --print-top-routes 10
```

### process_transit_map.sh — Full Pipeline (Layer 2)

Automates the entire flow: GTFS filtering → graph conversion → layout → SVG rendering → text adjustment.

```
Usage: ./process_transit_map.sh <gtfs_file> [options]

Data Filtering:
  -s, --stops <ids>           Comma-separated stop IDs to include
  -r, --routes <patterns>     Route patterns (supports wildcards, e.g. "138*")
  --route-ids <ids>           Comma-separated GTFS route_id (exact); or use -n instead
  -n, --top-routes <num>      N busiest routes by scheduled trips (`magga_cli.py --print-top-route-ids`)
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

# Top 100 routes → SVG (requires C++ tools in PATH; -lt caps loom runtime)
./process_transit_map.sh city_transit.zip -n 100 -m 1 -lt 600 -o output/top100_svg
```

**Output:**
```
output/
├── <name>.zip                    # Filtered GTFS subset
├── <name>_loom.json              # Intermediate graph data
├── <name>_geographic.svg         # Geographic layout map
└── <name>_schematic.svg          # Schematic (octilinear) map
```

### generate_all_stops.py — Batch Per-Stop Map Generation (Layer 3)

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

### gtfs_subset_cli.py — GTFS Filtering (Layer 3)

Create filtered subsets of GTFS data, optionally with an interactive HTML map. `process_transit_map.sh` calls this for `-s` / `-r` / `-m`; use the CLI directly for `--map`, `--route-ids`, or odd filenames.

```
Usage: python gtfs_subset_cli.py <input.zip> [options]

  -o, --output <path>         Output GTFS path (auto-generated if omitted)
  -s, --stops <ids>           Comma-separated stop IDs
  -r, --routes <patterns>     Route patterns (wildcards supported)
  --route-ids <ids>           Comma-separated route_id values (exact)
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

# Exact route_id list (from routes_trip_frequency.csv, etc.)
python gtfs_subset_cli.py city.zip --route-ids "24o,1jx" -o corridor.zip

# Custom visualization
python gtfs_subset_cli.py city.zip --map --color-by routes --cmap viridis
```

### gtfs_map_viewer.py — Interactive HTML Maps (Layer 3)

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

### adjust_svg.py — SVG Text Adjustment (Layer 3)

Scales text sizes in generated SVG maps for better readability.

```
Usage: python adjust_svg.py <input_svg> <output_svg> <scale_factor>

  scale_factor: e.g. 0.85 to shrink text to 85%, 1.2 to enlarge to 120%
```

### Kannada / Indic labels (Layer 3)

- `translate_gtfs_stops.py` — translate `stops.txt` names inside a GTFS zip (optional `deep-translator`).
- `svg_indic_font_fallback.py` — after `process_transit_map.sh`, ensures station labels use **Noto Sans Kannada first** (Ubuntu-first stacks break conjunct shaping). The shell script runs this automatically on final SVGs.

### Manual Pipeline (Layer 4)

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
| `magga_cli.py` | Stats + plots + top-route subsets (see [Command layers](#command-layers)) | `matplotlib`, full feed |
| `translate_gtfs_stops.py` | EN→KN (or other) `stop_name` translation in a zip | `deep-translator` (venv) |

```bash
# Parallel processing of multiple GTFS files
./process_gtfs.sh 'stop_analysis/subsets/*.zip'

# Process doublet stop pairs
./process_doublets.sh city_transit.zip
```

## Project Structure

```
magga/
├── magga_cli.py                # Layer 1: stats + plots + top-route subsets
├── export_gtfs_network_stats.py # Layer 3: CSV-only network rankings
├── network_stats.py            # Stop/route ranking helpers (used by magga_cli)
├── process_transit_map.sh      # Layer 2: GTFS → SVG pipeline
├── gtfs_subset_cli.py          # GTFS filtering CLI
├── generate_all_stops.py       # Batch per-stop map generation
├── magga_style.py              # Style configuration (colormaps, fonts, tiers)
├── stop_importance.py          # Stop scoring & distance computation
├── svg_layers.py               # SVG layer post-processor
├── svg_indic_font_fallback.py  # Kannada/Indic font fix for SVG labels
├── translate_gtfs_stops.py     # Optional GTFS stop_name translation
├── gtfs_map_viewer.py          # Interactive HTML map generator
├── gtfs_analysis.py            # GTFS analysis library
├── adjust_svg.py               # SVG text size adjuster
├── tests/                      # pytest (e.g. test_network_stats.py)
├── requirements.txt            # Python dependencies
├── pytest.ini
├── src/                        # C++ source code
│   ├── gtfs2graph/             #   GTFS → graph converter
│   ├── topo/                   #   Topology handler (edge overlap, clustering)
│   ├── loom/                   #   Line arrangement optimizer
│   ├── octi/                   #   Octilinear (schematic) layout
│   ├── transitmap/             #   SVG renderer with labels
│   ├── shared/                 #   Shared utilities
│   ├── cppgtfs/                #   GTFS C++ library (submodule)
│   └── util/                   #   Utility library (submodule)
├── examples/                   # Sample data; `examples/readme/*.png` = README screenshots
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

## Magga online

**[magga.kutuhula.in](https://magga.kutuhula.in)** — Made with ❤️ by [kutūhuḷa](https://magga.kutuhula.in).

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
