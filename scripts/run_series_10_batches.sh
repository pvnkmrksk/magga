#!/usr/bin/env bash
# One map per "series of 10": for prefix AB (00–99), routes AB0*, AB1*, … AB9*
# (same structure as 240–249: 240*,241*,…,249*). Only prefixes that appear in
# the feed as the first two digits of route_short_name are run.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${ROOT}/build:${PATH}"
export MAGGA_PYTHON="${MAGGA_PYTHON:-${ROOT}/.venv-kn-demo/bin/python}"

EN="${EN_FEED:-${ROOT}/bmtc-2.zip}"
OUT="${OUT_BASE:-${ROOT}/output/batch_series_10}"
MIN_TRIPS="${MIN_TRIPS:-10}"
LOOM="${LOOM_LIMIT:-600}"

if [[ ! -f "$EN" ]]; then echo "Missing feed: $EN" >&2; exit 1; fi

log() { echo "=== $(date -Iseconds) $*"; }

PREFIXES="$(
  EN="$EN" "$MAGGA_PYTHON" - <<'PY'
import os
import re
import partridge as ptg
feed = ptg.load_feed(os.environ["EN"])
names = feed.routes["route_short_name"].fillna("").astype(str)
pref = set()
for n in names:
    m = re.match(r"^(\d{2})", n)
    if m:
        pref.add(m.group(1))
for p in sorted(pref):
    print(p)
PY
)"

n=0
for p in $PREFIXES; do
  n=$((n + 1))
  patterns=$(
    seq 0 9 | while read -r d; do printf '%s%s*,' "$p" "$d"; done | sed 's/,$//'
  )
  label="${p}0-${p}9"
  od="${OUT}/en/routes/series_${label}"
  log "[$n] series ${label} → ${od}"
  mkdir -p "$od"
  if ! ./process_transit_map.sh "$EN" -r "$patterns" -m "$MIN_TRIPS" -lt "$LOOM" -o "$od"; then
    log "WARNING: series ${label} failed (continuing)"
  fi
done

log "Finished ${n} series batches → ${OUT}"
