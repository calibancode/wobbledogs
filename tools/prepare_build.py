#!/usr/bin/env python3
"""Repair decompiler artifacts in the freshly decompiled source.

ILSpy emits C# that is semantically correct but occasionally does not
round-trip through a C# compiler, because C# is more ambiguous than IL. Each
such fix lives as a documented unified diff under tools/patches/<assembly>/ and
is applied here, in lexical order, with `patch -p1` from that assembly's source
directory.

The step is idempotent: a patch that is already present is reported as such and
left alone. A manifest of what was applied (and each patch's sha256) is written
under $WD_DATA_DIR so a build can be traced back to an exact patch set.

Usage:
  tools/prepare_build.py
"""
from __future__ import annotations

import hashlib
import subprocess
import sys

import paths


def already_applied(target, patch_file) -> bool:
    probe = subprocess.run(
        ["patch", "-p1", "--reverse", "--dry-run", "--silent", "-d", str(target)],
        stdin=patch_file.open("rb"), capture_output=True,
    )
    return probe.returncode == 0


def apply_patch(target, patch_file) -> bool:
    result = subprocess.run(
        ["patch", "-p1", "--forward", "--silent", "-d", str(target)],
        stdin=patch_file.open("rb"), capture_output=True, text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout + result.stderr)
    return result.returncode == 0


def main() -> int:
    if not paths.SRC_DIR.is_dir():
        print("error: run tools/decompile.sh first", file=sys.stderr)
        return 1

    manifest: list[str] = []
    applied = skipped = 0

    for asm in paths.GAME_ASSEMBLIES:
        patch_dir = paths.PATCH_DIR / asm
        target = paths.SRC_DIR / asm
        if not patch_dir.is_dir():
            continue
        for patch_file in sorted(patch_dir.glob("*.patch")):
            if not target.is_dir():
                print(f"error: missing source dir {target}", file=sys.stderr)
                return 1
            digest = hashlib.sha256(patch_file.read_bytes()).hexdigest()
            if already_applied(target, patch_file):
                state = "already-applied"
                skipped += 1
            elif apply_patch(target, patch_file):
                state = "applied"
                applied += 1
            else:
                print(f"error: failed to apply {patch_file}", file=sys.stderr)
                return 1
            print(f"==> {state}: {asm}/{patch_file.name}")
            manifest.append(f"{digest}  {state}  {asm}/{patch_file.name}")

    manifest_path = paths.DATA_DIR / "prepare_build.txt"
    manifest_path.write_text(
        "# decompiler-artifact patches applied to decompiled source\n"
        "# sha256  state  patch\n" + "\n".join(manifest) + "\n"
    )
    print(f"==> {applied} applied, {skipped} already present; manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
