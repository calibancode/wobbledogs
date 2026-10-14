# Shared locations for the original game install and all generated data.
#
# Sourced by every tool. Override any of the WD_* variables with an absolute
# path to relocate that tree; keep them consistent across commands.

ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# The pristine Steam install (read-only; never written to).
WD_GAME_DIR="${WD_GAME_DIR:-/mnt/Games/SteamLibrary/steamapps/common/Wobbledogs/Wobbledogs_Windows_64}"
# Extracted originals + decompiled source (derived, copyright-bearing, ignored).
WD_DATA_DIR="${WD_DATA_DIR:-$ROOT/.local-data}"
# Build outputs: rebuilt assemblies, runnable tree, logs, reports.
WD_BUILD_DIR="${WD_BUILD_DIR:-$ROOT/build}"
# Proton compat-data (wine prefix) used to launch the game.
WD_PREFIX_DIR="${WD_PREFIX_DIR:-$WD_BUILD_DIR/proton-prefix}"

for _v in WD_GAME_DIR WD_DATA_DIR WD_BUILD_DIR WD_PREFIX_DIR; do
  _val="${!_v}"
  if [[ "$_val" != /* ]]; then
    echo "error: $_v must be an absolute path (got '$_val')" >&2
    exit 1
  fi
done
unset _v _val

export ROOT WD_GAME_DIR WD_DATA_DIR WD_BUILD_DIR WD_PREFIX_DIR

# `dotnet tool install --global` drops ilspycmd under ~/.dotnet/tools, which is
# not always on PATH. Add it if present so the decompile step works unattended.
if [[ -d "$HOME/.dotnet/tools" ]]; then
  case ":$PATH:" in
    *":$HOME/.dotnet/tools:"*) ;;
    *) export PATH="$PATH:$HOME/.dotnet/tools" ;;
  esac
fi

# Derived locations, fixed relative to the above.
DATA_MANAGED="$WD_DATA_DIR/original/Managed"   # pristine shipped assemblies
SRC_DIR="$WD_DATA_DIR/src"                     # decompiled C#
OBJ_DIR="$WD_BUILD_DIR/obj"                    # compiler response files
REBUILT_DIR="$WD_BUILD_DIR/rebuilt"            # rebuilt assemblies
OUT_DIR="$WD_BUILD_DIR/out"                    # runnable game tree
LOG_DIR="$WD_BUILD_DIR/logs"                   # build + run logs
MATCH_DIR="$WD_BUILD_DIR/code_match"           # code-match reports
PATCH_DIR="$ROOT/tools/patches"                # decompiler-artifact fixes

# Assemblies reconstructed from source, in dependency order.
GAME_ASSEMBLIES=(
  "Assembly-CSharp-firstpass"
  "Assembly-CSharp"
)

# C# language level for both ILSpy output and compilation. Unity 2019.4 compiled
# game code as C# 7.3; matching it keeps the emitted source shape (block-scoped
# namespaces, no primary constructors) and the generated IL closer to the
# original than a newer language level does.
ILSPY_LANGVERSION="${ILSPY_LANGVERSION:-CSharp7_3}"
CSC_LANGVERSION="${CSC_LANGVERSION:-7.3}"

export SRC_DIR OBJ_DIR REBUILT_DIR OUT_DIR LOG_DIR MATCH_DIR PATCH_DIR ILSPY_LANGVERSION CSC_LANGVERSION
