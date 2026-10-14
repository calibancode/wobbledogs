# Patches

Hand-authored fixes applied to the decompiled source by
`tools/prepare_build.py` before compilation.

Each subdirectory names a decompiled assembly (see `GAME_ASSEMBLIES` in
`tools/paths.sh`). Patches inside are applied in lexical order with `patch -p1`
from that assembly's source directory, and are idempotent — a patch that is
already present is reported as such and left alone.

These fix **decompiler artifacts**: places where ILSpy's C# output does not
round-trip through a C# compiler even though the original IL was perfectly
valid. C# is more ambiguous than IL, so this is occasional and expected.

Each patch file begins with a comment explaining the IL it came from, so the
repair can be checked against the original assembly.

The sha256 of every applied patch is recorded in
`$WD_DATA_DIR/prepare_build.txt`.
