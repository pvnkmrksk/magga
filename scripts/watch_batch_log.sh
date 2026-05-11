#!/usr/bin/env bash
# Follow Magga batch output in real time. Usage:
#   ./scripts/watch_batch_log.sh
#   ./scripts/watch_batch_log.sh /path/to/run.log
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="${1:-$ROOT/output/batch_run_all/run.log}"
if [[ ! -f "$LOG" ]]; then
  echo "Log not found: $LOG" >&2
  echo "Start a batch with stdout/stderr redirected, e.g.:" >&2
  echo "  ./run_all_batches.sh > output/batch_run_all/run.log 2>&1" >&2
  exit 1
fi
exec tail -n 80 -f "$LOG"
