# Build

Requires Bash, Python 3, GNU `patch`, `ilspycmd` (ILSpy), a .NET SDK providing
Roslyn `csc`, and — to run the result — Proton GE with a working GPU/Vulkan
stack.

```bash
dotnet tool install --global ilspycmd      # once
tools/export_all.sh                        # copy the shipped assemblies out of the install
tools/decompile.sh                         # ILSpy -> C#
tools/prepare_build.py                     # repair decompiler artifacts
tools/build.sh                             # recompile the assemblies
tools/package.sh                           # assemble a runnable tree
tools/run.sh rebuilt                       # launch it
tools/run.sh original                      # control: the pristine install
```

From a clean tree this takes about half a minute and never writes to the game
install. `tools/verify.sh` then measures the result (see
[VERIFICATION.md](VERIFICATION.md)).

The default game install is

```
/mnt/Games/SteamLibrary/steamapps/common/Wobbledogs/Wobbledogs_Windows_64
```

## Paths

Everything the tools read or write is set in `tools/paths.sh`
(`tools/paths.py` mirrors it for the Python tools). Override a `WD_*` variable
with an absolute path to relocate that tree, and keep it consistent across
commands.

| Variable | Default | Contents |
|---|---|---|
| `WD_GAME_DIR` | the Steam install above | The pristine game; only ever read |
| `WD_DATA_DIR` | `.local-data/` (ignored) | `original/` shipped assemblies, `src/` decompiled C#, `prepare_build.txt` |
| `WD_BUILD_DIR` | `build/` (ignored) | `obj/`, `rebuilt/`, `out/`, `logs/`, `code_match/`, `proton-prefix/` |

| Path | Contents |
|---|---|
| `$WD_DATA_DIR/original/Managed/` | Pristine shipped assemblies, also the compile references |
| `$WD_DATA_DIR/src/<assembly>/` | Decompiled C# |
| `build/rebuilt/` | The assemblies rebuilt from source |
| `build/out/` | Runnable tree: original assets symlinked, rebuilt assemblies real |
| `build/code_match/` | Code-match reports and worklists |

## Notes

Building uses ILSpy with `--languageversion CSharp7_3` and Roslyn `csc` at
`-langversion:7.3`, because Unity 2019.4 compiled the game as C# 7.3. Emitting
the same language level keeps the source shape (block-scoped namespaces, no
primary constructors) and the generated IL as close to the original as a newer
compiler allows. See [CODE_MATCH.md](CODE_MATCH.md) for the measured effect.

Compilation uses `-nostdlib` and references the game's own Mono profile
assemblies, so the framework the code is compiled against is the one it shipped
with. See [ARCHITECTURE.md](ARCHITECTURE.md) for why.

Edit source preparation by adding a documented patch under
`tools/patches/<assembly>/`; `tools/prepare_build.py` applies them idempotently
and records a manifest.

[Architecture](ARCHITECTURE.md) · [Verification](VERIFICATION.md)
