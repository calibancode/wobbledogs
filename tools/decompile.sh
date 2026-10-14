#!/usr/bin/env bash
#
# decompile.sh - decompile the game's own assemblies to C# under
# $WD_DATA_DIR/src/, one directory per assembly.
#
# Output is a derived work of the original (copyrighted) code, so it lives in
# the ignored data tree and is never committed.
#
# Usage:
#   tools/decompile.sh
#
# Requires: ilspycmd on PATH (`dotnet tool install --global ilspycmd`).
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tools/paths.sh"

command -v ilspycmd >/dev/null || {
  echo "error: ilspycmd not on PATH (dotnet tool install --global ilspycmd)" >&2
  exit 1
}
[[ -f "$DATA_MANAGED/Assembly-CSharp.dll" ]] || {
  echo "error: run tools/export_all.sh first" >&2
  exit 1
}

mkdir -p "$SRC_DIR"

for asm in "${GAME_ASSEMBLIES[@]}"; do
  dll="$DATA_MANAGED/$asm.dll"
  [[ -f "$dll" ]] || { echo "error: missing $dll" >&2; exit 1; }
  out="$SRC_DIR/$asm"
  echo "==> decompiling $asm (ILSpy language level $ILSPY_LANGVERSION)"
  rm -rf "$out"
  mkdir -p "$out"
  ilspycmd -p -o "$out" --nested-directories \
    --languageversion "$ILSPY_LANGVERSION" "$dll"
  echo "    $(find "$out" -name '*.cs' | wc -l) source files"
done

echo "==> decompiled source: $SRC_DIR"
