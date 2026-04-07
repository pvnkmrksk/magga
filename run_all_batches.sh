#!/usr/bin/env bash
# Run all batch_transit_maps pipelines (EN + KN when kn zip exists).
# Logs to stdout; redirect with: ./run_all_batches.sh > output/batch_run_all/run.log 2>&1
set -euo pipefail
cd "$(dirname "$0")"
export PATH="${PWD}/build:${PATH}"
export MAGGA_PYTHON="${MAGGA_PYTHON:-${PWD}/.venv-kn-demo/bin/python}"

EN="${EN_FEED:-bmtc-2.zip}"
KN="${KN_FEED:-output/bmtc-2-kn.zip}"
OUT="${OUT_BASE:-output/batch_run_all}"
# Parallel stop jobs per feed (GTFS load once per worker). EN+KN also run concurrently.
WORKERS="${WORKERS:-6}"
# Exclude the N busiest stops (importance rank); tail batch for smaller machines. Set 0 to disable.
SKIP_TOP_N="${SKIP_TOP_N:-100}"
# FLAT_LABELS=0 keeps distance tiers + progressive _full/_important SVG variants.
FLAT_ARGS=()
if [[ "${FLAT_LABELS:-1}" != "0" ]]; then
  FLAT_ARGS=(--flat-labels)
fi
SKIP_ARGS=()
if [[ "${SKIP_TOP_N}" != "0" ]]; then
  SKIP_ARGS=(--skip-top-n "${SKIP_TOP_N}")
fi

if [[ ! -f "$EN" ]]; then echo "Missing EN feed: $EN" >&2; exit 1; fi
if [[ ! -f "$KN" ]]; then echo "Warning: no KN feed at $KN — EN-only for stops batches" >&2; KN=""; fi

# Optional one-off:  python batch_transit_maps.py demo --en-feed bmtc-2.zip --out output/batch_run_all
echo "=== $(date -Iseconds) stops merged g50 (EN+KN), profiles default compact ==="
if [[ -n "$KN" ]]; then
  python batch_transit_maps.py stops --en-feed "$EN" --kn-feed "$KN" --out "$OUT" \
    --merge-names --max-groups 50 --profiles default compact --skip-existing \
    --workers "$WORKERS" "${SKIP_ARGS[@]}" "${FLAT_ARGS[@]}"
else
  python batch_transit_maps.py stops --en-feed "$EN" --out "$OUT" \
    --merge-names --max-groups 50 --profiles default compact --skip-existing \
    --workers "$WORKERS" "${SKIP_ARGS[@]}" "${FLAT_ARGS[@]}"
fi

echo "=== $(date -Iseconds) stops merged g100 → ${OUT}_merged_g100 ==="
if [[ -n "$KN" ]]; then
  python batch_transit_maps.py stops --en-feed "$EN" --kn-feed "$KN" --out "${OUT}_merged_g100" \
    --merge-names --max-groups 100 --profiles default compact --skip-existing \
    --workers "$WORKERS" "${SKIP_ARGS[@]}" "${FLAT_ARGS[@]}"
else
  python batch_transit_maps.py stops --en-feed "$EN" --out "${OUT}_merged_g100" \
    --merge-names --max-groups 100 --profiles default compact --skip-existing \
    --workers "$WORKERS" "${SKIP_ARGS[@]}" "${FLAT_ARGS[@]}"
fi

echo "=== $(date -Iseconds) stops least-first g100 → ${OUT}_least_g100 ==="
if [[ -n "$KN" ]]; then
  python batch_transit_maps.py stops --en-feed "$EN" --kn-feed "$KN" --out "${OUT}_least_g100" \
    --least-first --max-groups 100 --profiles default compact --skip-existing \
    --workers "$WORKERS" "${SKIP_ARGS[@]}" "${FLAT_ARGS[@]}"
else
  python batch_transit_maps.py stops --en-feed "$EN" --out "${OUT}_least_g100" \
    --least-first --max-groups 100 --profiles default compact --skip-existing \
    --workers "$WORKERS" "${SKIP_ARGS[@]}" "${FLAT_ARGS[@]}"
fi

echo "=== $(date -Iseconds) routes: 314* prefix + regex ^31[0-9] ==="
if [[ -n "$KN" ]]; then
  python batch_transit_maps.py routes --en-feed "$EN" --kn-feed "$KN" --out "$OUT" \
    --wildcard '314*' --regex '^31[0-9]'
else
  python batch_transit_maps.py routes --en-feed "$EN" --out "$OUT" \
    --wildcard '314*' --regex '^31[0-9]'
fi

echo "=== $(date -Iseconds) ALL BATCHES FINISHED ==="
