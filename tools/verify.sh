#!/usr/bin/env bash
#
# verify.sh - measure how faithfully the rebuilt assemblies reproduce the
# shipped ones, and check the measurement tools themselves.
#
# Runs the byte-weighted code-match measurement against the saved baseline in
# docs/reference/ (a regression fails the check) and then the unit tests.
#
# Usage:
#   tools/verify.sh
#
# Requires: the assemblies have been rebuilt (tools/build.sh) and ilspycmd is on
# PATH. The saved baseline is refreshed by copying build/code_match/report.json
# to docs/reference/code_match_report.json once a change has been reviewed.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tools/paths.sh"

[[ -d "$REBUILT_DIR" ]] || { echo "error: run tools/build.sh first" >&2; exit 1; }

echo "=============== code match ==============="
python3 "$ROOT/tools/measure_code.py" \
  --baseline "$ROOT/docs/reference/code_match_report.json"

echo
echo "=============== unit tests ==============="
python3 -m unittest discover -s "$ROOT/tools/code_match" -p 'test_*.py'

echo
echo "Worklist of differing bodies:"
for asm in "${GAME_ASSEMBLIES[@]}"; do
  tsv="$MATCH_DIR/$asm-diffs.tsv"
  [[ -f "$tsv" ]] && echo "  $tsv ($(($(wc -l < "$tsv") - 1)) entries)"
done
