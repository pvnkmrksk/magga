"""
Optional GTFS entity labels from JSON (e.g. Kannada), keyed by ``route_id`` or ``stop_id``.

The same file shape is used for routes and stops:

  - Flat: {"entity_id": "ಕನ್ನಡ ಲೇಬಲ್"}
  - Per-language: {"entity_id": {"kn": "…", "en": "…"}}

Part of Magga (ಮಗ್ಗ/मग್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping

import pandas as pd


def load_route_label_map(path: Path, *, lang: str = "kn") -> Dict[str, str]:
    """Load ``route_id`` or ``stop_id`` → display string; dict values pick ``lang`` or ``default``."""
    raw: Mapping[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    out: Dict[str, str] = {}
    for k, v in raw.items():
        rid = str(k)
        if isinstance(v, dict):
            label = v.get(lang) or v.get("default")
            if label is None and v:
                label = next(iter(v.values()))
            if label is None:
                continue
            out[rid] = str(label)
        elif v is not None:
            out[rid] = str(v)
    return out


def merge_route_display_labels(
    routes_df: pd.DataFrame,
    mapping: Mapping[str, str],
    *,
    fallback_col: str = "route_short_name",
) -> pd.Series:
    """One label per row; unmapped routes use ``fallback_col`` (then '?')."""
    rids = routes_df["route_id"].astype(str)
    fb = routes_df[fallback_col].astype(str).fillna("?")
    # dict lookup: unknown keys → NaN → fallback
    mapped = rids.map(dict(mapping))
    return mapped.fillna(fb)
