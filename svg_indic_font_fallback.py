#!/usr/bin/env python3
"""
Fix Indic text rendering in Magga / transitmap SVG output.

Putting Latin fonts first (e.g. Ubuntu Condensed) causes browsers to run
per-glyph fallback for Kannada code points, which breaks OpenType conjuncts
(ligatures look “dead”). Station labels must use an Indic-capable font
**first** (Noto Sans Kannada).

Line labels (route numbers) stay Latin-first.

Also sets xml:lang on <svg> and station <text> for better shaper behavior.

Part of Magga (ಮಗ್ಗ/मग್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Kannada shaping needs this family to win itemization, not fall back per glyph.
STATION_FONT = 'font-family="Noto Sans Kannada, Noto Sans, sans-serif"'
LINE_FONT = 'font-family="Ubuntu, Noto Sans, sans-serif"'


def apply_fallback(svg_text: str) -> str:
    lines = []
    for line in svg_text.splitlines(keepends=True):
        if re.search(r'class="station-label"', line):
            line = re.sub(r'font-family="[^"]*"', STATION_FONT, line)
            if "xml:lang=" not in line:
                line = re.sub(r"(<(?:[\w]+:)?text\b)", r'\1 xml:lang="kn"', line, count=1)
        elif re.search(r'class="line-label"', line):
            line = re.sub(r'font-family="[^"]*"', LINE_FONT, line)
        elif 'font-family="Ubuntu Condensed"' in line:
            line = line.replace('font-family="Ubuntu Condensed"', STATION_FONT)
        lines.append(line)

    text = "".join(lines)
    head = text[:800]
    if "xml:lang=" not in head:
        text = re.sub(r"(<(?:[\w]+:)?svg\b)", r'\1 xml:lang="kn"', text, count=1)
    return text


def main() -> None:
    p = argparse.ArgumentParser(
        description="Fix Kannada/Indic shaping in transit SVGs (Noto first on station labels)."
    )
    p.add_argument("svg", nargs="+", help="SVG file(s) to patch in place")
    p.add_argument(
        "-o",
        "--output",
        help="Optional single output path (only when exactly one input svg)",
    )
    args = p.parse_args()

    if args.output and len(args.svg) != 1:
        print("--output requires exactly one input file", file=sys.stderr)
        sys.exit(1)

    for path_str in args.svg:
        path = Path(path_str)
        raw = path.read_text(encoding="utf-8")
        patched = apply_fallback(raw)
        dest = Path(args.output) if args.output else path
        dest.write_text(patched, encoding="utf-8")
        print(f"Patched {dest}", file=sys.stderr)


if __name__ == "__main__":
    main()
