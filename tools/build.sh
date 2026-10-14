#!/usr/bin/env bash
#
# build.sh - independently rebuild the game's managed assemblies from the
# decompiled C#.
#
# Compilation runs the Roslyn compiler shipped in the .NET SDK with -nostdlib,
# so every reference (mscorlib, System, System.Core, the Unity module
# assemblies, ...) comes from the game's own Mono profile copies in
# $WD_DATA_DIR/original/Managed. That reproduces the original compilation
# environment far more closely than a stock net40/net472 targeting pack, whose
# System.Core conflicts with the game's own and leaves
# System.Runtime.CompilerServices.ExtensionAttribute unresolvable.
#
# Assembly-CSharp-firstpass is rebuilt first and the result is used as the
# reference when compiling Assembly-CSharp, so the whole chain is rebuilt from
# source rather than leaning on a shipped assembly.
#
# Usage:
#   tools/build.sh
#
# Requires: a .NET SDK (for Roslyn csc), tools/decompile.sh already run.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/tools/paths.sh"

CSC_DLL="${CSC_DLL:-$(find /usr/share/dotnet/sdk -maxdepth 4 -path '*/Roslyn/bincore/csc.dll' | sort -V | tail -1)}"
[[ -n "$CSC_DLL" ]] || { echo "error: Roslyn csc.dll not found under /usr/share/dotnet/sdk" >&2; exit 1; }
[[ -d "$SRC_DIR" ]] || { echo "error: run tools/decompile.sh first" >&2; exit 1; }

echo "==> using Roslyn: $CSC_DLL"
mkdir -p "$OBJ_DIR" "$REBUILT_DIR" "$LOG_DIR"

declare -A REBUILT=()

compile_assembly() {
  local asm="$1" src="$SRC_DIR/$1" rsp="$OBJ_DIR/$1.rsp" out="$OBJ_DIR/$1.dll"
  [[ -d "$src" ]] || { echo "error: missing source dir $src" >&2; return 1; }

  {
    echo "-target:library"
    echo "-out:$out"
    echo "-nostdlib"          # framework types come from the game's own runtime
    echo "-unsafe"
    echo "-optimize+"
    echo "-deterministic"
    echo "-nologo"
    echo "-langversion:$CSC_LANGVERSION"
    echo "-warnaserror-"
    echo "-nowarn:0436,0169,0649,0414,0219"   # decompiler-noise warnings

    # Reference every shipped assembly except the one being rebuilt and any
    # already rebuilt, which is supplied from obj/ instead.
    local dll base
    for dll in "$DATA_MANAGED"/*.dll; do
      base="$(basename "$dll" .dll)"
      [[ "$base" == "$asm" ]] && continue
      [[ -n "${REBUILT[$base]:-}" ]] && continue
      echo "-r:$dll"
    done
    for base in "${!REBUILT[@]}"; do
      echo "-r:${REBUILT[$base]}"
    done

    find "$src" -name '*.cs' -print0 | sort -z | while IFS= read -r -d '' f; do
      printf '"%s"\n' "$f"
    done
  } > "$rsp"

  echo "==> compiling $asm"
  if ! dotnet "$CSC_DLL" "@$rsp" > "$LOG_DIR/compile-$asm.log" 2>&1; then
    echo "error: compilation failed for $asm" >&2
    grep -E 'error ' "$LOG_DIR/compile-$asm.log" | head -40 >&2
    echo "    (full log: $LOG_DIR/compile-$asm.log)" >&2
    return 1
  fi
  echo "    ok: $asm.dll ($(stat -c%s "$out") bytes, \
$(grep -cE 'warning ' "$LOG_DIR/compile-$asm.log" || true) warnings)"

  cp -f "$out" "$REBUILT_DIR/$asm.dll"
  REBUILT["$asm"]="$out"
}

for asm in "${GAME_ASSEMBLIES[@]}"; do
  compile_assembly "$asm"
done

echo "==> rebuilt assemblies:"
ls -la "$REBUILT_DIR"
