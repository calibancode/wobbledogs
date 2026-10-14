#!/usr/bin/env bash
#
# verify_runtime.sh - verify that the rebuilt tree boots exactly like the
# original, by launching it and comparing the normalised Unity player log
# against the saved baseline.
#
# Usage:
#   tools/verify_runtime.sh            # boot the rebuild and compare
#   tools/verify_runtime.sh --capture  # re-capture the baseline from the
#                                      # pristine install (needs a display)
#
# The baseline in docs/reference/boot_baseline.txt was captured from the
# pristine install through the same Proton invocation. Only paths, timing
# numbers and Enlighten thread ids are normalised away; any other difference is
# reported and fails the check.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tools/paths.sh"

BASELINE="$ROOT/docs/reference/boot_baseline.txt"
CAPTURE=0
[[ "${1:-}" == "--capture" ]] && CAPTURE=1

if [[ $CAPTURE -eq 1 ]]; then
  echo "==> capturing baseline from the pristine install"
  "$ROOT/tools/run.sh" original --post 20
  python3 "$ROOT/tools/normalize_player_log.py" \
    "$LOG_DIR/original/Player.log" "$BASELINE"
  echo "==> baseline written: $BASELINE"
  exit 0
fi

[[ -f "$BASELINE" ]] || {
  echo "error: no baseline; run tools/verify_runtime.sh --capture" >&2; exit 1; }

echo "==> booting the rebuilt tree"
"$ROOT/tools/run.sh" rebuilt --post 20

LOG="$LOG_DIR/rebuilt/Player.log"
[[ -f "$LOG" ]] || { echo "error: no player log produced at $LOG" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 "$ROOT/tools/normalize_player_log.py" "$LOG" "$TMP/rebuilt.txt"

echo
if diff -u --label "baseline (original)" "$BASELINE" \
           --label "rebuilt" "$TMP/rebuilt.txt" > "$TMP/diff.txt"; then
  echo "==> boot parity: OK ($(wc -l < "$TMP/rebuilt.txt") normalised log lines identical)"
  exit 0
fi

echo "==> boot parity: DIFFERENCES"
sed -n '1,120p' "$TMP/diff.txt"
echo
echo "Explained differences remain differences; investigate before dismissing."
exit 1
