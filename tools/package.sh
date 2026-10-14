#!/usr/bin/env bash
#
# package.sh - assemble a runnable game tree under $WD_BUILD_DIR/out.
#
# Every original file is exposed as a symlink back into the read-only install,
# so the multi-hundred-megabyte art/audio payload is not copied and the original
# install is never written to. Only the assemblies rebuilt from source are real
# files, replacing the shipped ones. The directories are real, so Unity can
# still create its output_log.txt alongside the data folder.
#
# A manifest of the substitution is written next to the tree for provenance.
#
# Usage:
#   tools/package.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tools/paths.sh"

[[ -d "$WD_GAME_DIR" ]] || { echo "error: game dir not found: $WD_GAME_DIR" >&2; exit 1; }
[[ -d "$REBUILT_DIR" ]] || { echo "error: run tools/build.sh first" >&2; exit 1; }

echo "==> linking original assets (no copies)"
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"
while IFS= read -r -d '' rel; do
  dest="$OUT_DIR/$rel"
  mkdir -p "$(dirname "$dest")"
  ln -sfn "$WD_GAME_DIR/$rel" "$dest"
done < <(cd "$WD_GAME_DIR" && find . -type f -printf '%P\0')

echo "==> installing rebuilt assemblies"
replaced=()
for asm in "${GAME_ASSEMBLIES[@]}"; do
  dll="$REBUILT_DIR/$asm.dll"
  [[ -f "$dll" ]] || { echo "error: missing rebuilt $dll" >&2; exit 1; }
  dest="$OUT_DIR/Wobbledogs_Data/Managed/$asm.dll"
  rm -f "$dest"
  cp -f "$dll" "$dest"
  replaced+=("Wobbledogs_Data/Managed/$asm.dll")
done

{
  echo "# Rebuilt assemblies substituted into the game tree"
  echo "# generated $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  for rel in "${replaced[@]}"; do
    printf '%s  %s  (original %s bytes, rebuilt %s bytes)\n' \
      "$(sha256sum "$OUT_DIR/$rel" | cut -d' ' -f1)" "$rel" \
      "$(stat -c%s "$WD_GAME_DIR/$rel")" "$(stat -c%s "$OUT_DIR/$rel")"
  done
} > "$OUT_DIR/REBUILD-MANIFEST.txt"

echo "==> runnable tree: $OUT_DIR"
cat "$OUT_DIR/REBUILD-MANIFEST.txt"
