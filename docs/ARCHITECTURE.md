# Architecture

## Why decompile and recompile

The shipped `Assembly-CSharp.dll` and `Assembly-CSharp-firstpass.dll` are
ordinary managed assemblies; their IL is complete and readable. The highest
fidelity reconstruction practical without the original Unity project is
therefore:

1. decompile the IL to C#;
2. recompile that C# with a compatible compiler;
3. substitute the result into the otherwise untouched game tree.

All gameplay stays in source form; nothing is hand-reimplemented. Recovering the
Unity project (scenes, prefabs, materials) with an asset extractor is a larger,
separate undertaking and is listed as future work.

| Assembly | Role |
|---|---|
| `Assembly-CSharp-firstpass.dll` | Vendor code: Steamworks.NET, InControl helpers, image effects, dev console, … |
| `Assembly-CSharp.dll` | The game itself (Animal Uprising) |

Everything else in the install — the Unity engine, `mscorlib`, art, audio,
levels — is an immutable input.

## Toolchain choices

**Decompiler: ILSpy** (`ilspycmd -p --nested-directories`). Emits a compilable
project layout with idiomatic C#, organised by namespace.

**Compiler: the Roslyn `csc` bundled with the .NET SDK, driven directly.** Not
`dotnet build`, for two reasons:

* The generated projects target `net40`. On Linux that pulls in
  `Microsoft.NETFramework.ReferenceAssemblies`, whose `System.Core.dll` conflicts
  with the game's own (`could not determine a winner because
  'Platform:System.Core.dll' has no file version`) and leaves
  `System.Runtime.CompilerServices.ExtensionAttribute` unresolvable.
* Driving `csc` directly allows **`-nostdlib` plus references to the game's own
  Mono profile assemblies** (`$WD_DATA_DIR/original/Managed/*.dll`). The same
  `mscorlib`, `System`, `System.Core`, `System.Xml` and Unity module assemblies
  at the same versions means the compilation environment matches the original's
  far better than any stock targeting pack.

**Language level: C# 7.3, both when decompiling and when compiling.** Unity
2019.4 compiled game code as C# 7.3. Matching it keeps the emitted source shape
and suppresses the modern compiler's synthesis of `EmbeddedAttribute` /
`RefSafetyRulesAttribute`, so the rebuilt type surface matches the original's
exactly. Measured effect, in matching hand-authored bodies and before the
local-slot normalisation was introduced: `Assembly-CSharp` rose from 10,623 to
10,677 and `Assembly-CSharp-firstpass` from 3,356 to 3,358, and the spurious
extra types disappeared entirely. Both settings are configurable in
`tools/paths.sh` (`ILSPY_LANGVERSION`, `CSC_LANGVERSION`).

**Compile order.** `Assembly-CSharp-firstpass` is rebuilt first and the result
used as the reference when compiling `Assembly-CSharp`, so the chain is rebuilt
from source rather than leaning on a shipped assembly.

## Decompiler artifacts and the patch set

ILSpy's output is semantically correct but occasionally does not round-trip
through a C# compiler, because C# is more ambiguous than IL. One such case was
found:

`FloraGUI.Awake` calls `OpenAllFloraPage(bool, bool, bool)` with
`(false, true, false)` (IL_003b–IL_003e). ILSpy renders it as an argument-less
`OpenAllFloraPage()`, which is ambiguous between the 1- and 3-argument overloads
because both have all-optional parameters. The patch in
`tools/patches/Assembly-CSharp/` spells the arguments out, restoring the exact
call the IL performs. Patches carry a header comment explaining the IL they come
from and are recorded with their hashes in `$WD_DATA_DIR/prepare_build.txt`.

## Packaging

`tools/package.sh` builds `build/out/` from **symlinks** to every original file,
with only the rebuilt assemblies present as real files. This keeps the
multi-hundred-megabyte art/audio payload out of the build output, keeps the
original install strictly read-only, and makes the substitution set obvious
(`REBUILD-MANIFEST.txt` records it). Directories are real, so Unity can still
create its `output_log.txt` alongside the data folder.

## Runner

The game is launched through **Proton GE** rather than a bare Wine prefix:
Proton supplies DXVK/vkd3d and Media Foundation plumbing, and the shipped title
behaves consistently under it. `STEAM_COMPAT_DATA_PATH` points at
`build/proton-prefix/`, so the prefix is part of the ignored build tree.

Proton runs the game inside a pressure-vessel container where `/tmp` is always
visible but arbitrary repository sub-paths may not be, so `tools/run.sh` writes
the Unity log to `/tmp` and copies it into `build/logs/` afterwards.

## Control

`tools/run.sh original` runs the pristine install through the same Proton
invocation and writes to `build/logs/original/`. Comparing the two player logs
is the primary correctness evidence; see [VERIFICATION.md](VERIFICATION.md).
