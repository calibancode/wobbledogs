# Wobbledogs
[![code matched](https://img.shields.io/badge/code_matched-69.80%25-blue)](docs/CODE_MATCH.md)
[![boot parity](https://img.shields.io/badge/boot_parity-pass-brightgreen)](docs/VERIFICATION.md)

Reconstructs the Steam Windows release of Wobbledogs (app `1424330`, "Animal
Uprising") from its managed assemblies: a Unity 2019.4.23f1 (Mono, x86-64)
game whose gameplay ships as IL.

```bash
tools/export_all.sh              # copy the shipped assemblies out of the install
tools/decompile.sh               # ILSpy -> C#
tools/prepare_build.py           # repair decompiler artifacts
tools/build.sh                   # recompile with Roslyn against the game's own Mono profile
tools/package.sh                 # assemble a runnable tree
tools/run.sh rebuilt             # launch it through Proton; `original` runs the control
tools/verify.sh                  # code-match measurement + unit tests
tools/verify_runtime.sh          # boot parity against the saved baseline
```

[Build](docs/BUILD.md) · [Verification](docs/VERIFICATION.md) ·
[Code matching](docs/CODE_MATCH.md) · [Architecture](docs/ARCHITECTURE.md) ·
[Game mechanics](docs/GAME_MECHANICS.md) · [Save format](docs/SAVE_FORMAT.md) ·
[Code map](docs/CODE_MAP.md)

## Layout

| Path | Contents |
|---|---|
| `tools/` | Extraction, decompilation, build, launch and verification tooling |
| `tools/patches/` | Documented fixes for decompiler artifacts |
| `docs/` | Hand-written documentation; `docs/reference/` holds the saved comparison baselines |

Build output is written to `build/` and `.local-data/`, both ignored. See
[BUILD.md](docs/BUILD.md) for every path and how to relocate it.

## Licence

MIT — see [LICENSE](LICENSE). It covers the original tooling and documentation
in this repository only.

Wobbledogs is copyright Animal Uprising / Tom Astle. This project is not
affiliated with or endorsed by the rights holders, and no rights to the game or
its assets are granted here. You need to own a legitimate copy to run any of it.
