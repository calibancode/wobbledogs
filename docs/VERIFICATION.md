# Verification

[Code matching](CODE_MATCH.md): **69.80 %** —
**743,607 / 1,065,339 original code bytes** across both reconstructed
assemblies, with **14,133 / 15,738 hand-authored bodies matching**; every
hand-authored body is present except seven empty static constructors.
**Boot parity: 100 %** — the rebuilt tree's normalised player log is identical
to the pristine install's.

```bash
tools/verify.sh            # code-match measurement vs the saved baseline + unit tests
tools/verify_runtime.sh    # boot the rebuild and diff its player log vs the baseline
```

## Boot parity

`tools/verify_runtime.sh` launches `build/out` through the same Proton
invocation used for the pristine install, then compares the normalised Unity
player log against the saved baseline in
[`reference/boot_baseline.txt`](reference/boot_baseline.txt), captured from the
original with `--capture`.

Normalisation rewrites only values that legitimately vary between runs: absolute
paths under the game, data and build roots; assembly-reload and unload times;
and Enlighten worker thread ids. Any other difference is reported and fails.

Current result: **all 57 normalised lines identical.** The rebuilt game boots
through Mono/Unity initialisation, D3D11 device creation, script reload, physics
and input initialisation to its first scene, exactly as the original does, and
stays running until closed.

## Code matching

See [CODE_MATCH.md](CODE_MATCH.md) for the definition, the saved report, and the
worklist of differing bodies. The headline is the byte-weighted match of
hand-authored method bodies after normalising compiler implementation details.

## What is *not* verified

* **Semantic equivalence.** Byte-similar IL is evidence, not proof. No gameplay
  behaviour, save-file round trip, physics or rendering output has been compared
  against the original.
* **The Steam path.** `[Steamworks.NET] SteamAPI_Init() failed` is logged because
  the game is launched outside the Steam client — exactly as the original logs
  it in the same situation. Achievements, overlay and Steam cloud are untested
  in the rebuild.
* **Audio and video.** The intro/menu media and audio are decoded by Proton; no
  comparison of their output has been made.
* **Non-code metadata.** Class layout, custom attributes, resource and
  non-code-data equivalence are outside the measurement.
* **Bit-exactness.** Rebuilds are reproducible (identical sha256 across repeated
  builds) but not bit-identical to the shipped assemblies.

## Reproducibility

Repeated `tools/build.sh` runs produce byte-identical output (the compiler is
invoked deterministically). Rebuilding from a clean `build/` and
`.local-data/` reproduces the same assemblies and the same measured scores.

The saved comparison baselines under `docs/reference/` are the reference point:
`tools/verify.sh` fails if the headline code-match score regresses, and
`tools/verify_runtime.sh` fails on any unexpected log difference.

[Code matching](CODE_MATCH.md) · [Architecture](ARCHITECTURE.md)
