"""Shared locations for the original game install and all generated data.

Mirrors tools/paths.sh so Python tools and shell tools agree on every path.
Override any of the WD_* variables with an absolute path; keep them consistent
across commands.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# `dotnet tool install --global` drops ilspycmd under ~/.dotnet/tools, which is
# not always on PATH. Mirror tools/paths.sh so Python tools find it too.
_DOTNET_TOOLS = Path.home() / ".dotnet" / "tools"
if _DOTNET_TOOLS.is_dir() and str(_DOTNET_TOOLS) not in os.environ.get("PATH", "").split(os.pathsep):
    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + str(_DOTNET_TOOLS)


def _abs(name: str, default: Path) -> Path:
    value = Path(os.environ.get(name, default))
    if not value.is_absolute():
        raise ValueError(f"{name} must be an absolute path (got {value})")
    return value


GAME_DIR = _abs("WD_GAME_DIR", Path(
    "/mnt/Games/SteamLibrary/steamapps/common/Wobbledogs/Wobbledogs_Windows_64"))
DATA_DIR = _abs("WD_DATA_DIR", ROOT / ".local-data")
BUILD_DIR = _abs("WD_BUILD_DIR", ROOT / "build")
PREFIX_DIR = _abs("WD_PREFIX_DIR", BUILD_DIR / "proton-prefix")

# Derived locations, fixed relative to the above.
DATA_MANAGED = DATA_DIR / "original" / "Managed"
SRC_DIR = DATA_DIR / "src"
OBJ_DIR = BUILD_DIR / "obj"
REBUILT_DIR = BUILD_DIR / "rebuilt"
OUT_DIR = BUILD_DIR / "out"
LOG_DIR = BUILD_DIR / "logs"
MATCH_DIR = BUILD_DIR / "code_match"
PATCH_DIR = ROOT / "tools" / "patches"
REFERENCE_DIR = ROOT / "docs" / "reference"

GAME_ASSEMBLIES = ("Assembly-CSharp-firstpass", "Assembly-CSharp")
