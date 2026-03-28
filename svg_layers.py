"""
SVG Layers — Post-process SVGs with semantic layers, tiers, and backdrop composition.

Part of the Magga (ಮಗ್ಗ/मग्ग) project: https://github.com/pvnkmrksk/magga
License: GPL-3.0 — see LICENSE file.
"""

import copy
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union

from magga_style import MaggaStyle

# Inkscape namespace for layer support
INKSCAPE_NS = "http://www.inkscape.org/namespaces/inkscape"
SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"

# Register namespaces so they're preserved in output
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)
ET.register_namespace("inkscape", INKSCAPE_NS)


def _classify_element(elem: ET.Element) -> Optional[str]:
    """Classify an SVG element by its transit map role based on CSS classes."""
    cls = elem.get("class", "")
    if "transit-edge-outline" in cls:
        return "route-outline"
    if "transit-edge" in cls:
        return "route"
    if "inner-geom-outline" in cls:
        return "connection-outline"
    if "inner-geom" in cls:
        return "connection"
    if "station-poly" in cls:
        return "station"
    if "line-label" in cls:
        return "line-label"
    if "station-label" in cls:
        return "station-label"
    return None


def _classify_group(group: ET.Element) -> Optional[str]:
    """Classify a top-level <g> by examining its children."""
    children = list(group)
    if not children:
        return None

    # Check first non-defs child
    for child in children:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "defs":
            continue
        role = _classify_element(child)
        if role:
            return role
        # Check for station polygons
        if tag == "polygon" and "station-poly" in child.get("class", ""):
            return "station"
    return None


def _extract_station_name(label_elem: ET.Element) -> str:
    """Extract station name text from a station-label <text> element."""
    # The text is inside <textPath> element
    for child in label_elem.iter():
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "textPath":
            text = (child.text or "").strip()
            if text:
                return text
            # Sometimes text is in tail of sub-elements
            for sub in child:
                if sub.tail and sub.tail.strip():
                    return sub.tail.strip()
    return ""


def _make_layer(layer_id: str, label: str) -> ET.Element:
    """Create an SVG <g> element that Inkscape recognizes as a layer."""
    g = ET.Element(f"{{{SVG_NS}}}g")
    g.set("id", layer_id)
    g.set(f"{{{INKSCAPE_NS}}}label", label)
    g.set(f"{{{INKSCAPE_NS}}}groupmode", "layer")
    return g


def add_svg_layers(
    input_svg: Union[str, Path],
    output_svg: Union[str, Path],
    tier_data: Optional[Dict[str, int]] = None,
    style: Optional[MaggaStyle] = None,
) -> None:
    """Restructure a transit map SVG with semantic, Inkscape-compatible layers.

    The C++ transitmap tool outputs SVG with anonymous <g> groups. This function
    reorganizes them into named layers that designers can toggle in Inkscape/Illustrator.

    Layers created:
      - "Route Outlines" — black outline strokes behind routes
      - "Routes" — colored transit line polylines
      - "Node Connections" — junction inner geometry (outlines + colored)
      - "Stations" — white station polygons with black stroke
      - "Line Labels" — route number labels along curves
      - "Station Labels (All)" — all station name labels (if no tier_data)

    With tier_data (dict mapping station_name → tier int):
      - "Station Labels - Tier 1 (Nearby)" — closest stops, always visible
      - "Station Labels - Tier 2 (Important)" — mid-distance important stops
      - "Station Labels - Tier 3 (Junctions)" — distant major junctions
      - "Station Labels - Tier 4 (Hidden)" — hidden by default (display:none)

    Args:
        input_svg: Path to input SVG from transitmap.
        output_svg: Path to write layered SVG.
        tier_data: Optional dict of {station_name: tier_number}.
        style: Optional style config (unused currently, reserved for future).
    """
    tree = ET.parse(str(input_svg))
    root = tree.getroot()

    # Collect all defs from anywhere in the tree
    all_defs = ET.Element(f"{{{SVG_NS}}}defs")
    for defs_elem in root.iter(f"{{{SVG_NS}}}defs"):
        for child in list(defs_elem):
            all_defs.append(child)
    # Also check non-namespaced
    for defs_elem in root.iter("defs"):
        for child in list(defs_elem):
            all_defs.append(child)

    # Create layer groups
    layer_route_outlines = _make_layer("layer-route-outlines", "Route Outlines")
    layer_routes = _make_layer("layer-routes", "Routes")
    layer_conn = _make_layer("layer-connections", "Node Connections")
    layer_stations = _make_layer("layer-stations", "Stations")
    layer_line_labels = _make_layer("layer-line-labels", "Line Labels")

    # Station label layers depend on tier_data
    if tier_data:
        label_layers = {
            1: _make_layer("layer-station-labels-tier1", "Station Labels - Tier 1 (Nearby)"),
            2: _make_layer("layer-station-labels-tier2", "Station Labels - Tier 2 (Important)"),
            3: _make_layer("layer-station-labels-tier3", "Station Labels - Tier 3 (Junctions)"),
            4: _make_layer("layer-station-labels-tier4", "Station Labels - Tier 4 (Hidden)"),
        }
        # Tier 4 hidden by default
        label_layers[4].set("style", "display:none")
    else:
        label_layers = {
            0: _make_layer("layer-station-labels", "Station Labels"),
        }

    # Process all top-level groups
    ns_g = f"{{{SVG_NS}}}g"
    top_groups = [child for child in root if child.tag in (ns_g, "g")]

    for group in top_groups:
        role = _classify_group(group)

        if role in ("route-outline", "route"):
            # This group has interleaved outline + route polylines
            for child in list(group):
                cls = child.get("class", "")
                if "outline" in cls:
                    layer_route_outlines.append(child)
                else:
                    layer_routes.append(child)

        elif role in ("connection-outline", "connection"):
            # Inner geometry groups — keep together
            for child in list(group):
                layer_conn.append(child)

        elif role == "station":
            for child in list(group):
                layer_stations.append(child)

        elif role == "line-label":
            # Line labels with their defs
            for child in list(group):
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "defs":
                    for d in list(child):
                        all_defs.append(d)
                else:
                    layer_line_labels.append(child)

        elif role == "station-label":
            # Station labels — sort into tiers
            # Collect label+defs pairs
            pending_defs = []
            for child in list(group):
                tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
                if tag == "defs":
                    pending_defs.extend(list(child))
                elif tag == "text":
                    name = _extract_station_name(child)
                    if tier_data:
                        tier = _get_tier_for_name(name, tier_data)
                        target = label_layers.get(tier, label_layers.get(4))
                    else:
                        target = label_layers[0]
                    # Add any pending defs to the global defs
                    for d in pending_defs:
                        all_defs.append(d)
                    pending_defs = []
                    target.append(child)

    # Clear the root and rebuild
    for child in list(root):
        root.remove(child)

    # Add consolidated defs
    root.append(all_defs)

    # Add layers in rendering order (back to front)
    root.append(layer_route_outlines)
    root.append(layer_routes)
    root.append(layer_conn)
    root.append(layer_stations)
    root.append(layer_line_labels)
    for tier in sorted(label_layers.keys()):
        root.append(label_layers[tier])

    tree.write(str(output_svg), encoding="utf-8", xml_declaration=True)


def _get_tier_for_name(name: str, tier_data: Dict[str, int]) -> int:
    """Look up tier for a station name, with fuzzy matching."""
    # Exact match
    if name in tier_data:
        return tier_data[name]
    # Try case-insensitive
    name_lower = name.lower().strip()
    for key, tier in tier_data.items():
        if key.lower().strip() == name_lower:
            return tier
    # Try partial match (station name may be truncated in SVG)
    for key, tier in tier_data.items():
        if name_lower in key.lower() or key.lower() in name_lower:
            return tier
    # Default to tier 4 (hidden) if no match
    return 4


def compose_with_backdrop(
    foreground_svg: Union[str, Path],
    backdrop_svg: Union[str, Path],
    output_svg: Union[str, Path],
    style: Optional[MaggaStyle] = None,
) -> None:
    """Merge an HF corridor SVG as a faint backdrop behind the foreground map.

    The backdrop is inserted as the bottommost layer with reduced opacity.

    Args:
        foreground_svg: Path to the main (foreground) SVG.
        backdrop_svg: Path to the HF corridor SVG.
        output_svg: Path to write the composed SVG.
        style: Style config for backdrop_opacity (default: 0.15).
    """
    if style is None:
        style = MaggaStyle()

    fg_tree = ET.parse(str(foreground_svg))
    fg_root = fg_tree.getroot()

    bd_tree = ET.parse(str(backdrop_svg))
    bd_root = bd_tree.getroot()

    # Create backdrop layer group
    backdrop_layer = _make_layer("layer-backdrop", "HF Corridor Backdrop")
    backdrop_layer.set("style", f"opacity:{style.backdrop_opacity}")

    # Copy all backdrop content into the layer
    for child in list(bd_root):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "defs":
            # Merge defs into foreground's defs
            fg_defs = fg_root.find(f"{{{SVG_NS}}}defs")
            if fg_defs is None:
                fg_defs = fg_root.find("defs")
            if fg_defs is None:
                fg_defs = ET.SubElement(fg_root, f"{{{SVG_NS}}}defs")
            for d in list(child):
                # Prefix IDs to avoid collisions
                elem_id = d.get("id", "")
                if elem_id:
                    d.set("id", f"bd-{elem_id}")
                fg_defs.append(d)
        else:
            backdrop_layer.append(child)

    # Insert backdrop as first child after defs
    defs_idx = 0
    for i, child in enumerate(fg_root):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag == "defs":
            defs_idx = i + 1
            break
    fg_root.insert(defs_idx, backdrop_layer)

    fg_tree.write(str(output_svg), encoding="utf-8", xml_declaration=True)


def apply_progressive_hiding(
    svg_path: Union[str, Path],
    output_dir: Union[str, Path],
    base_name: str = "map",
) -> Dict[str, Path]:
    """Generate multiple SVG variants with different tier visibility levels.

    Creates:
      - {base_name}.svg — all tiers visible
      - {base_name}_important.svg — tiers 1+2 visible, 3+4 hidden
      - {base_name}_junctions.svg — tiers 1+2+3 visible, 4 hidden
      - {base_name}_minimal.svg — all station labels hidden, only routes/stations

    Args:
        svg_path: Path to a layered SVG (output of add_svg_layers with tier_data).
        output_dir: Directory to write variant SVGs.
        base_name: Base filename for variants.

    Returns:
        Dict mapping variant name to output path.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    variants = {
        "full": {"hide_tiers": set(), "hide_labels": False},
        "important": {"hide_tiers": {3, 4}, "hide_labels": False},
        "junctions": {"hide_tiers": {4}, "hide_labels": False},
        "minimal": {"hide_tiers": {1, 2, 3, 4}, "hide_labels": True},
    }

    outputs = {}
    for variant_name, config in variants.items():
        tree = ET.parse(str(svg_path))
        root = tree.getroot()

        suffix = f"_{variant_name}" if variant_name != "full" else ""
        out_path = output_dir / f"{base_name}{suffix}.svg"

        for elem in root.iter():
            elem_id = elem.get("id", "")

            # Hide tier groups
            for tier in config["hide_tiers"]:
                if elem_id == f"layer-station-labels-tier{tier}":
                    elem.set("style", "display:none")

            # Hide all station labels in minimal mode
            if config["hide_labels"]:
                if "layer-station-labels" in elem_id:
                    elem.set("style", "display:none")
                if elem_id == "layer-line-labels":
                    elem.set("style", "display:none")

        tree.write(str(out_path), encoding="utf-8", xml_declaration=True)
        outputs[variant_name] = out_path

    return outputs
