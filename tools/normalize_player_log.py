#!/usr/bin/env python3
"""Normalise a Unity Player.log so two runs of the same build can be compared.

The log is the primary runtime evidence: if the original install and the
rebuilt tree boot identically, their normalised logs are identical. Only the
values that legitimately differ between two runs are rewritten:

  * absolute paths under the game / data / build roots become <ROOT>
  * timing numbers (assembly reload, unload time) become <TIME>
  * Enlighten worker thread ids become <ID>

Usage:
  tools/normalize_player_log.py IN [OUT]     # OUT defaults to stdout
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import paths  # noqa: E402

ROOTS = [str(paths.GAME_DIR), str(paths.OUT_DIR), str(paths.REBUILT_DIR),
         str(paths.DATA_DIR), str(paths.BUILD_DIR), str(paths.ROOT)]

RULES = [
    (re.compile(r"- Completed reload, in\s+[0-9.]+ seconds"), "- Completed reload, in <TIME> seconds"),
    (re.compile(r"UnloadTime:\s*[0-9.]+ ms"), "UnloadTime: <TIME> ms"),
    (re.compile(r"Thread -> id:\s*[0-9a-fA-F]+"), "Thread -> id: <ID>"),
]


def normalize(text: str) -> str:
    # Longest roots first so /a/b/c is replaced before /a/b.
    for root in sorted(ROOTS, key=len, reverse=True):
        text = text.replace(root, "<ROOT>")
    for pattern, replacement in RULES:
        text = pattern.sub(replacement, text)
    return text


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    src = Path(sys.argv[1])
    if not src.is_file():
        print(f"error: no such log: {src}", file=sys.stderr)
        return 1
    result = normalize(src.read_text(errors="replace"))
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(result)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
