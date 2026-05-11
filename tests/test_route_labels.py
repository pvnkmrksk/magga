"""Route label JSON loading and merge."""

import json

import pandas as pd

from route_labels import load_route_label_map, merge_route_display_labels


def test_load_flat_and_nested(tmp_path):
    p = tmp_path / "l.json"
    p.write_text(
        json.dumps(
            {
                "a": "ಎ",
                "b": {"kn": "ಬಿ", "en": "B"},
            }
        ),
        encoding="utf-8",
    )
    m = load_route_label_map(p, lang="kn")
    assert m["a"] == "ಎ"
    assert m["b"] == "ಬಿ"
    m_en = load_route_label_map(p, lang="en")
    assert m_en["b"] == "B"


def test_merge_fallback():
    df = pd.DataFrame(
        {
            "route_id": ["x", "y"],
            "route_short_name": ["1", "2"],
        }
    )
    out = merge_route_display_labels(df, {"x": "kn-x"})
    assert out.tolist() == ["kn-x", "2"]
