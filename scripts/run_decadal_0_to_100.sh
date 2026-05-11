#!/usr/bin/env bash
# Eleven "decadal" batches from 0–9 through 100–109 (same style as 240–249 but
# for each tens band):
#   00–09: 00*,01*,…,09*
#   10–19: 10*,11*,…,19*
#   …
#   90–99: 90*,91*,…,99*
#  100–109: 100*,101*,…,109*
#
# This is NOT the same as two-digit-prefix series (e.g. prefix 24 → only 240–249):
# here "10–19" uses 10*,…,19* so it also picks up 10-J, 115, etc., not only 100–109.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PATH="${ROOT}/build:${PATH}"
export MAGGA_PYTHON="${MAGGA_PYTHON:-${ROOT}/.venv-kn-demo/bin/python}"

EN="${EN_FEED:-${ROOT}/bmtc-2.zip}"
OUT="${OUT_BASE:-${ROOT}/output/batch_decadal_0_100}"
MIN_TRIPS="${MIN_TRIPS:-10}"
LOOM="${LOOM_LIMIT:-600}"

if [[ ! -f "$EN" ]]; then echo "Missing feed: $EN" >&2; exit 1; fi

log() { echo "=== $(date -Iseconds) $*"; }

run_decadal() {
  local label=$1
  local patterns=$2
  local od="${OUT}/en/routes/decadal_${label}"
  log "decadal ${label} → ${od}"
  mkdir -p "$od"
  if ./process_transit_map.sh "$EN" -r "$patterns" -m "$MIN_TRIPS" -lt "$LOOM" -o "$od"; then
    log "ok ${label}"
  else
    log "SKIP/FAIL ${label} (no matching routes or pipeline error — common for 00–09 on BMTC)"
  fi
}

# 0–9 … 90–99  (00*…09* is often empty in BMTC — no routes starting with 00, 01, …)
for b in $(seq 0 9); do
  base=$((b * 10))
  patterns=$(
    seq 0 9 | while read -r u; do printf '%02d*,' "$((base + u))"; done | sed 's/,$//'
  )
  printf -v label "%02d-%02d" "$base" $((base + 9))
  run_decadal "$label" "$patterns"
done

# 100–109 (three-digit head — usually very few routes named 100–109 in BMTC)
patterns=$(
  seq 100 109 | while read -r n; do printf '%s*,' "$n"; done | sed 's/,$//'
)
run_decadal "100-109" "$patterns"

log "Finished decadal 0–100 pass → ${OUT}"
