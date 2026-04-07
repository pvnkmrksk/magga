#!/usr/bin/env bash
# Route + stop batches: decade route families (0–9 … 90–99), 401*, KBS, G-, K-,
# then least-frequency stops (top 100 by ascending trip_count).
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="${PWD}/build:${PATH}"
export MAGGA_PYTHON="${MAGGA_PYTHON:-${PWD}/.venv-kn-demo/bin/python}"
PY="${MAGGA_PYTHON}"

EN="${EN_FEED:-bmtc-2.zip}"
KN="${KN_FEED:-output/bmtc-2-kn.zip}"
OUT="${OUT_BASE:-output/magga_user_batches}"
MIN_TRIPS="${MIN_TRIPS:-10}"
LOOM="${LOOM_LIMIT:-600}"
WORKERS="${WORKERS:-6}"

if [[ ! -f "$EN" ]]; then echo "Missing EN feed: $EN" >&2; exit 1; fi

log() { echo "=== $(date -Iseconds) $*"; }

# --- 1) Two-digit prefix “decades”: 00*…09*, 10*…19*, … 90*…99*
# (NOT 0*,1*,…,9* — a lone 3* matches 3.* and wrongly includes 30, 302, 3-J, …)
log "Route prefix decades 00–09 … 90–99 (min_trips=$MIN_TRIPS)"
for b in $(seq 0 9); do
  base=$((b * 10))
  patterns=$(
    seq 0 9 | while read -r u; do printf '%02d*,' "$((base + u))"; done | sed 's/,$//'
  )
  printf -v label "%02d-%02d" "$base" $((base + 9))
  od="${OUT}/en/routes/decade_${label}"
  log "Decade ${label} → ${od}"
  mkdir -p "$od"
  ./process_transit_map.sh "$EN" -r "$patterns" -m "$MIN_TRIPS" -lt "$LOOM" -o "$od"
done

# --- 2) 401*, KBS (substring), G-*, K- (regex; excludes KIA/KBS)
log "Special route families: 401*, *KBS*, G-*, ^K-"
"$PY" batch_transit_maps.py routes --en-feed "$EN" --out "$OUT" \
  --wildcard '401*' \
  --wildcard '*KBS*' \
  --wildcard 'G-*' \
  --regex '^K-' \
  -m "$MIN_TRIPS" \
  --loom-limit "$LOOM"

# --- 3) Lowest trip_count stops, cap 100 (least-first)
log "Stops: least-first, max 100 (EN+KN if KN exists)"
STOP_ARGS=(
  --least-first
  --max-groups 100
  --profiles default compact
  --skip-existing
  --workers "$WORKERS"
  --min-trips 5
)
if [[ -f "$KN" ]]; then
  "$PY" batch_transit_maps.py stops --en-feed "$EN" --kn-feed "$KN" --out "$OUT" "${STOP_ARGS[@]}"
else
  log "No KN feed at $KN — EN only for stops"
  "$PY" batch_transit_maps.py stops --en-feed "$EN" --out "$OUT" "${STOP_ARGS[@]}"
fi

log "ALL DONE"
