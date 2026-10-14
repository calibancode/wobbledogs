# Code matching

Measured 2026-10-13 with ilspycmd 11.1.0 / ICSharpCode.Decompiler 11.1.0, C# 7.3
source and compilation.

| Scope | Matching original code bytes | Code matched | Matching method bodies |
|---|---:|---:|---:|
| Reconstructed application (both assemblies) | 743,607 / 1,065,339 | **69.80 %** | 14,133 / 15,738 |
| `Assembly-CSharp` (the game) | 666,809 / 970,990 | 68.67 % | 10,771 / 12,309 |
| `Assembly-CSharp-firstpass` (vendor) | 76,798 / 94,349 | 81.40 % | 3,362 / 3,429 |

Every hand-authored *method body* is present except seven **empty** static
constructors (bodies containing nothing but `ret`) that Unity's compiler emitted
and modern Roslyn elides; they have no behavioural effect. There are no extra
hand-authored bodies.

## Definition

    code matched = original IL code bytes in identically-matching method bodies
                   ---------------------------------------------------------
                   original IL code bytes in all scoped method bodies

Every body receives all its original byte weight or none. Bodies that are
missing keep their denominator weight; extra bodies earn no credit. Constant
pools, resources and container bytes are not part of that weight. This measures
*code reconstruction* — not gameplay coverage, and not semantic equivalence.

The scope is the two assemblies this project reconstructs. Compiler-synthesised
members — lambda caches (`<>c`), closures (`<>c__DisplayClass…`) and
iterator/async state machines (`<…>d__…`) — are renumbered by every compiler and
can never be matched by name; they are excluded, because including them would
understate fidelity by construction. (Including them, "all methods" scores
65.55 %.)

Matching compares decoded opcodes and operands after normalising away:

* absolute addresses and header/code-size comments;
* `.maxstack` (evaluation-stack layout, not semantics);
* IL label numbering (renumbered in order of first appearance);
* whitespace;
* **local-variable slot numbering and encoding** — slots renumbered in order of
  first use, `ldloc.0`/`ldloc.s 3` canonicalised. Unity's compiler and modern
  Roslyn assign the same variables to different slots; that is a compiler
  implementation detail, not a reconstruction difference. Normalising it moves
  the headline from 66.80 % to 69.80 %.

Branch-target identity, call targets, signatures, member references, literal
values and constant types all remain significant. No opcode aliases or semantic
rewrites are applied.

## Remaining differences

The 322,000 unmatched bytes are dominated by a handful of large bodies. The
classes of difference, each verified by inspection:

1. **Local slot assignment.** Already normalised away (see above).
2. **Equivalent expression forms chosen by ILSpy.** Example:
   `DogLooks::UpdateBodySize` compiles the original's `−a + b` (IL: `neg` then
   `add`) but ILSpy renders the same expression as `b − a`, which Roslyn lowers
   to `b; a; sub`. Identical result, different bytes.
3. **Compiler instruction selection.** `ldc.i4.0` vs `ldc.i4.s 0`, operand
   evaluation ordering, string dedup.

These are all explained, but **explained differences remain differences** — none
of them is proven semantically equivalent, and none is normalised away except
local slots.

The full per-body worklist is
[`reference/code_match_differences.tsv`](reference/code_match_differences.tsv)
(2,192 entries: 1,883 differ, 151 extra generated, 158 missing generated).

## Reproduce

```bash
tools/measure_code.py                      # measure, compare with the baseline
tools/verify.sh                            # measure + unit tests
tools/measure_code.py --show 'DogLooks::UpdateBodySize'   # triage one body
```

Requires `ilspycmd`. Output is written to `build/code_match/`. The saved
[report](reference/code_match_report.json) records both assemblies' sha256, the
ILSpy version, and every scope's counts, so a result can be traced to an exact
input.

`tools/code_match/test_measure_code.py` covers the normaliser and the weighting
rules (missing bodies keep their weight, extra bodies earn no credit), and runs
under `python3 -m unittest discover -s tools/code_match -p 'test_*.py'`.

[Verification](VERIFICATION.md) · [Build](BUILD.md)
