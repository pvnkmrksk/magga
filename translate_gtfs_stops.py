#!/usr/bin/env python3
"""
Translate stop_name inside a GTFS zip (e.g. English → Kannada).

How it works
------------
1. Unpack the zip in memory (all files copied through unchanged except ``stops.txt``).
2. Read ``stops.txt`` with pandas.
3. Translate ``stop_name`` using ``deep_translator.GoogleTranslator``, which calls
   Google Translate’s public web endpoint (unofficial; fine for experiments, not
   for production SLAs). For production, use Google Cloud Translation API and
   swap the translate call.
4. Batching: ``translate_batch()`` sends multiple names per request (far faster
   than one HTTP round-trip per stop).
5. Optional ``--cache`` JSON (stop_id → translated name) lets you resume if the
   run stops mid-way; re-run with the same ``--cache`` path.

Install (venv recommended)::

    python3 -m venv .venv && source .venv/bin/activate
    pip install deep-translator pandas

Example::

    python translate_gtfs_stops.py bmtc-2.zip bmtc-2-kn.zip --batch-size 50 --sleep 0.5 \\
        --cache output/bmtc2_kn_stop_cache.json

Part of Magga (ಮಗ್ಗ/मग್ಗ): https://github.com/pvnkmrksk/magga
License: GPL-3.0
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
import unicodedata
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd


def load_cache(path: Path) -> Dict[str, str]:
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {str(k): str(v) for k, v in data.items()}
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: could not load cache {path}: {e}", file=sys.stderr)
        return {}


def save_cache(path: Path, cache: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=0)
    tmp.replace(path)


def normalize_indic(s: str) -> str:
    """Prefer NFC so combining marks form canonical clusters for shaping."""
    return unicodedata.normalize("NFC", s)


def translate_one_by_one(translator, texts: List[str]) -> List[str]:
    out: List[str] = []
    for t in texts:
        try:
            out.append(normalize_indic(translator.translate(t)))
        except Exception:
            out.append(t)
    return out


def translate_batch_safe(translator, texts: List[str]) -> List[str]:
    if not texts:
        return []
    try:
        batch = translator.translate_batch(texts)
        if len(batch) != len(texts):
            raise ValueError(f"batch length {len(batch)} != {len(texts)}")
        return [normalize_indic(x) for x in batch]
    except Exception as e:
        print(f"  batch failed ({e!r}), falling back to single strings", file=sys.stderr)
        return translate_one_by_one(translator, texts)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Translate GTFS stop_name fields inside a zip (e.g. en → kn)."
    )
    parser.add_argument("input_zip", help="Input GTFS .zip")
    parser.add_argument("output_zip", help="Output GTFS .zip")
    parser.add_argument("--target", default="kn", help="Target language code (default: kn)")
    parser.add_argument("--source", default="en", help="Source language code (default: en)")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        metavar="N",
        help="Names per translate_batch call (default: 50)",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=0.5,
        metavar="SEC",
        help="Pause between batches to reduce rate limiting (default: 0.5)",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=None,
        help="JSON path: stop_id → translated name; updated after each batch (resume)",
    )
    args = parser.parse_args()

    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        print(
            "Missing dependency: pip install deep-translator\n"
            "(Use a virtual environment; avoid PEP 668 system Python.)",
            file=sys.stderr,
        )
        sys.exit(1)

    inp = Path(args.input_zip)
    if not inp.is_file():
        print(f"Not found: {inp}", file=sys.stderr)
        sys.exit(1)

    translator = GoogleTranslator(source=args.source, target=args.target)
    cache: Dict[str, str] = load_cache(args.cache) if args.cache else {}
    out_buffers: dict[str, bytes] = {}

    with zipfile.ZipFile(inp, "r") as zin:
        for info in zin.infolist():
            name = info.filename
            data = zin.read(name)
            base = Path(name).name
            if base != "stops.txt":
                out_buffers[name] = data
                continue

            df = pd.read_csv(io.BytesIO(data), dtype=str, keep_default_na=False)
            if "stop_name" not in df.columns or "stop_id" not in df.columns:
                print("stops.txt needs stop_id and stop_name columns", file=sys.stderr)
                sys.exit(1)

            ids = df["stop_id"].astype(str).tolist()
            orig_names = df["stop_name"].astype(str).tolist()
            n = len(df)
            new_names: List[Optional[str]] = [None] * n

            pending: List[Tuple[int, str, str]] = []
            for i, (sid, nm) in enumerate(zip(ids, orig_names)):
                if sid in cache:
                    new_names[i] = cache[sid]
                    continue
                stripped = nm.strip()
                if not stripped:
                    new_names[i] = nm
                    cache[sid] = nm
                    continue
                pending.append((i, sid, stripped))

            total_pending = len(pending)
            done = 0
            bs = max(1, args.batch_size)

            for start in range(0, total_pending, bs):
                chunk = pending[start : start + bs]
                idxs = [c[0] for c in chunk]
                sids = [c[1] for c in chunk]
                texts = [c[2] for c in chunk]
                outs = translate_batch_safe(translator, texts)
                for i, sid, o in zip(idxs, sids, outs):
                    new_names[i] = o
                    cache[sid] = o
                done += len(chunk)
                if args.cache:
                    save_cache(args.cache, cache)
                print(f"  translated {done}/{total_pending} pending ({n} total stops)", file=sys.stderr)
                if args.sleep > 0 and start + bs < total_pending:
                    time.sleep(args.sleep)

            for i in range(n):
                if new_names[i] is None:
                    new_names[i] = orig_names[i]

            df["stop_name"] = [new_names[i] for i in range(n)]
            buf = io.StringIO()
            df.to_csv(buf, index=False)
            out_buffers[name] = buf.getvalue().encode("utf-8")

    outp = Path(args.output_zip)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(outp, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name in sorted(out_buffers.keys()):
            zout.writestr(name, out_buffers[name])

    print(f"Wrote {outp}", file=sys.stderr)


if __name__ == "__main__":
    main()
