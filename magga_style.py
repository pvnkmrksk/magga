"""
Magga Style — Central style and configuration for transit map generation.

Part of the Magga (ಮಗ್ಗ/मग्ग) project: https://github.com/pvnkmrksk/magga
License: GPL-3.0 — see LICENSE file.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class MaggaStyle:
    """Style configuration for Magga transit map generation.

    Controls visual appearance, progressive hiding thresholds, and backdrop
    settings. Can be loaded from / saved to JSON files.

    Example:
        >>> style = MaggaStyle(line_width=25, text_shrink=0.8)
        >>> style.save('my_style.json')
        >>> style = MaggaStyle.from_file('my_style.json')
    """

    # -- Colormaps --
    route_cmap: str = "tab20c"       # matplotlib colormap for route lines
    stop_cmap: str = "magma"         # matplotlib colormap for stop importance
    backdrop_cmap: str = "Greys"     # matplotlib colormap for HF corridor backdrop

    # -- Fonts (matches C++ transitmap defaults) --
    station_font: str = "Ubuntu Condensed"
    line_font: str = "Ubuntu"

    # -- Line sizing --
    line_width: float = 20.0         # width of transit lines (px)
    line_spacing: float = 10.0       # gap between parallel lines (px)
    outline_width: float = 1.0       # stroke outline width (px)

    # -- Label sizing --
    station_label_size: float = 60.0  # station name font size (px)
    line_label_size: float = 40.0     # route number font size (px)

    # -- Text post-processing --
    text_shrink: float = 0.85        # scale factor for adjust_svg (0-1)

    # -- Layout --
    smoothing: float = 20.0          # topo smoothing factor
    max_aggr_dist: float = 150.0     # topo max aggregation distance (meters)
    padding: float = -1.0            # SVG padding (-1 = auto)

    # -- Progressive hiding tiers --
    # Distance thresholds (meters) from focal stop defining tier boundaries.
    # tier 1: 0 to tier_distances[0]      -> show all labels
    # tier 2: tier_distances[0] to [1]    -> show stops with >= tier2_min_routes
    # tier 3: tier_distances[1] to [2]    -> show stops with >= tier3_min_routes
    # tier 4: beyond tier_distances[2]    -> dots only, no labels
    tier_distances: List[float] = field(default_factory=lambda: [500.0, 1500.0, 3000.0])
    tier2_min_routes: int = 3         # min routes for tier 2 label visibility
    tier3_min_routes: int = 5         # min routes for tier 3 (major junctions)

    # -- Importance scoring weights --
    importance_trip_weight: float = 0.4
    importance_route_weight: float = 0.6

    # -- HF corridor backdrop --
    backdrop_opacity: float = 0.15   # opacity for backdrop layer (0-1)
    backdrop_min_trips: int = 50     # routes with >= this many trips count as HF

    # -- Transit mode --
    transit_mode: str = "all"        # gtfs2graph -m flag: all, bus, tram, rail, etc.

    def to_transitmap_flags(self) -> str:
        """Generate command-line flags for the C++ transitmap tool."""
        return (
            f"--line-width {self.line_width} "
            f"--line-spacing {self.line_spacing} "
            f"--outline-width {self.outline_width} "
            f"--station-label-textsize {self.station_label_size} "
            f"--line-label-textsize {self.line_label_size} "
            f"--padding {self.padding} "
            f"--labels --tight-stations --render-dir-markers"
        )

    def to_topo_flags(self) -> str:
        """Generate command-line flags for the C++ topo tool."""
        return f"--smooth {self.smoothing} -d {self.max_aggr_dist}"

    def to_gtfs2graph_flags(self) -> str:
        """Generate command-line flags for the C++ gtfs2graph tool."""
        return f"-m {self.transit_mode}"

    def save(self, path: Union[str, Path]) -> None:
        """Save style configuration to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "MaggaStyle":
        """Load style configuration from a JSON file.

        Unknown keys in the file are silently ignored, making configs
        forward-compatible.
        """
        with open(path) as f:
            data = json.load(f)
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    @classmethod
    def from_file_or_default(cls, path: Optional[Union[str, Path]] = None) -> "MaggaStyle":
        """Load from file if path provided and exists, otherwise return defaults."""
        if path and Path(path).exists():
            return cls.from_file(path)
        return cls()
