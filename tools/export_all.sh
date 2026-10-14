#!/usr/bin/env bash
#
# export_all.sh - copy the shipped managed assemblies out of the pristine Steam
# install into $WD_DATA_DIR/original/Managed.
#
# Those copies serve as compile-time reference assemblies and as the untouched
# "original" side of every later comparison. The game install itself is only
# read. Re-running is idempotent.
#
# Usage:
#   tools/export_all.sh [PATH_TO_GAME_DIR]
#
# Default game dir is the Linux Steam install location; override with
# WD_GAME_DIR or the positional argument.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tools/paths.sh"

GAME="${1:-$WD_GAME_DIR}"
MANAGED="$GAME/Wobbledogs_Data/Managed"

if [[ ! -d "$MANAGED" ]]; then
  echo "error: no managed assemblies at '$MANAGED'" >&2
  echo "usage: $0 [PATH_TO_GAME_DIR]" >&2
  exit 1
fi

echo "==> copying shipped managed assemblies"
rm -rf "$DATA_MANAGED"
mkdir -p "$DATA_MANAGED"
cp -a "$MANAGED/." "$DATA_MANAGED/"

# Record a baseline of the assemblies this project reconstructs, so later steps
# (and comparisons) can tell whether the input install has changed.
{
  echo "# sha256 of the shipped assemblies this project reconstructs"
  for asm in "${GAME_ASSEMBLIES[@]}"; do
    sha256sum "$DATA_MANAGED/$asm.dll"
  done
} > "$WD_DATA_DIR/original/SHA256SUMS"

echo "==> $(find "$DATA_MANAGED" -name '*.dll' | wc -l) assemblies -> $DATA_MANAGED"
cat "$WD_DATA_DIR/original/SHA256SUMS"
