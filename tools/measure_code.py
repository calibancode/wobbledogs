#!/usr/bin/env python3
"""Measure how faithfully the rebuilt assemblies reproduce the shipped ones.

Dumps IL for both sides with ILSpy and compares per method after normalising
away things that legitimately vary between two compilations of the same source
(absolute addresses, `.maxstack`, IL label numbering, whitespace).

Headline metric, in the spirit of a byte-weighted code match:

    code matched = original IL code bytes in identically-matching method bodies
                   ---------------------------------------------------------
                   original IL code bytes in all scoped method bodies

Every scoped body receives all its original byte weight or none; bodies that are
missing keep their denominator weight, extra bodies earn no credit. This is a
measure of *code reconstruction*, not of gameplay coverage or semantic
equivalence, and it says nothing about non-code metadata.

Compiler-synthesised members (lambdas, closures, iterator/async state machines)
are renumbered by every compiler and can never be matched by name, so they are
reported separately and excluded from the "hand-authored" scope.

Usage:
  tools/measure_code.py                    # measure both assemblies
  tools/measure_code.py --assembly Assembly-CSharp.dll

Outputs:
  $WD_BUILD_DIR/code_match/<assembly>.json          per-assembly report
  $WD_BUILD_DIR/code_match/<assembly>-diffs.tsv     per-method worklist
  $WD_BUILD_DIR/code_match/report.json              combined, saved baseline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import paths

METHOD_RE = re.compile(r"^\s*\.method\b")
END_RE = re.compile(r"^\s*\}\s*//\s*end of method\s+(.*)$")
CODESIZE_RE = re.compile(r"//\s*Code size:\s*(\d+)")
LABEL_RE = re.compile(r"\bIL_[0-9a-fA-F]{4}\b")

# Compiler-synthesised members: lambda caches, closure classes and iterator /
# async state machines.
GENERATED_RE = re.compile(r"<>|<[^<>]*>[cd]__|<[^<>]*>b__")


def is_generated(key: str) -> bool:
    return bool(GENERATED_RE.search(key))


def normalize_body(lines: list[str]) -> str:
    """Reduce a method's IL text to a comparison-stable form."""
    out: list[str] = []
    labels: dict[str, str] = {}
    for raw in lines:
        if raw.lstrip().startswith("//"):
            continue
        line = re.sub(r"\s*//.*$", "", raw).strip()
        if not line or line.startswith(".maxstack"):
            continue
        line = LABEL_RE.sub(lambda m: labels.setdefault(m.group(0), f"IL_{len(labels):04d}"), line)
        out.append(re.sub(r"\s+", " ", line))
    return "\n".join(out)


# Local-variable access. Two compilations of the same source may assign
# variables to different slots (Roslyn does not preserve Unity's ordering), and
# may pick the short (`ldloc.0`) or long (`ldloc.s 3`) encoding accordingly.
LOCAL_OP_RE = re.compile(r"\b(ldloc|stloc|ldloca)(?:\.([0-3])|\.s\s+(\d+))\b")
LOCAL_DECL_RE = re.compile(r"^\[(\d+)\]\s*(.+?),?$")


def relax_locals(strict_text: str) -> str:
    """Canonicalise local-slot numbering and encoding.

    Slots are renumbered in order of first use; the locals declaration is
    rewritten in that order; every access is emitted in its long form. This
    removes a difference that is purely a compiler implementation detail -- the
    same source assigned to different slots, exactly what Unity's compiler and
    modern Roslyn disagree about -- without hiding any change to the code.
    """
    lines = strict_text.splitlines()
    decls: dict[int, str] = {}
    instrs: list[str] = []
    inside_locals = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(".locals"):
            inside_locals = True
        if inside_locals:
            match = LOCAL_DECL_RE.match(stripped)
            if match:
                decls[int(match.group(1))] = match.group(2).strip()
            if ")" in stripped:
                inside_locals = False
            continue
        instrs.append(line)

    order: dict[int, int] = {}

    def canon(slot: int) -> int:
        return order.setdefault(slot, len(order))

    def rewrite(match: "re.Match[str]") -> str:
        op = match.group(1)
        slot = int(match.group(2)) if match.group(2) is not None else int(match.group(3))
        return f"{op} {canon(slot)}"

    rewritten = [LOCAL_OP_RE.sub(rewrite, line) for line in instrs]

    # Unused declared slots still occupy a slot; keep them, in declaration order.
    for slot in sorted(decls):
        canon(slot)
    canonical_decls = ", ".join(decls.get(s, "?") for s, _ in sorted(order.items(), key=lambda kv: kv[1]))

    return f".locals ({canonical_decls})\n" + "\n".join(rewritten)


@dataclass
class Body:
    key: str
    code_bytes: int
    strict: str = ""
    relaxed: str = ""


@dataclass
class Assembly:
    name: str
    path: Path
    sha256: str
    bodies: dict[str, Body] = field(default_factory=dict)


def dump_il(ilspycmd: str, dll: Path, out: Path) -> None:
    with out.open("w") as fh:
        subprocess.run([ilspycmd, "-il", str(dll)],
                       stdout=fh, stderr=subprocess.DEVNULL, check=True)


def parse_bodies(text: str) -> dict[str, Body]:
    bodies: dict[str, Body] = {}
    header: str | None = None
    lines: list[str] = []
    code_bytes = 0
    for line in text.splitlines():
        if header is None:
            if METHOD_RE.match(line):
                header, lines, code_bytes = line.strip(), [], 0
            continue
        size = CODESIZE_RE.search(line)
        if size:
            code_bytes = int(size.group(1))
        end = END_RE.match(line)
        if not end:
            lines.append(line)
            continue
        key = end.group(1).strip() or header
        if key in bodies:                       # disambiguate overloads
            key = f"{key}#{header}"
        n, base = 2, key
        while key in bodies:
            key, n = f"{base}@{n}", n + 1
        strict = normalize_body(lines)
        bodies[key] = Body(key, code_bytes, strict, relax_locals(strict))
        header = None
    return bodies


def load(ilspycmd: str, dll: Path, tmp: Path) -> Assembly:
    il = tmp / f"{dll.stem}.il"
    dump_il(ilspycmd, dll, il)
    return Assembly(dll.name, dll,
                    hashlib.sha256(dll.read_bytes()).hexdigest(),
                    parse_bodies(il.read_text(errors="replace")))


def compare(orig: Assembly, new: Assembly, scope_filter, form: str = "strict") -> dict:
    orig_bodies = {k: v for k, v in orig.bodies.items() if scope_filter(k)}
    new_bodies = {k: v for k, v in new.bodies.items() if scope_filter(k)}

    total = sum(b.code_bytes for b in orig_bodies.values())
    matched = missing = differing = extra = 0
    match_bytes = 0
    diffs: list[tuple[str, str, int]] = []
    for key, body in sorted(orig_bodies.items()):
        other = new_bodies.get(key)
        if other is None:
            missing += 1
            diffs.append((key, "missing", body.code_bytes))
        elif getattr(other, form) == getattr(body, form):
            matched += 1
            match_bytes += body.code_bytes
        else:
            differing += 1
            diffs.append((key, "differs", body.code_bytes))
    for key in sorted(set(new_bodies) - set(orig_bodies)):
        extra += 1
        diffs.append((key, "extra", 0))

    return {
        "bodies": len(orig_bodies),
        "bodies_matched": matched,
        "bodies_differing": differing,
        "bodies_missing": missing,
        "bodies_extra": extra,
        "code_bytes": total,
        "code_bytes_matched": match_bytes,
        "code_matched": (match_bytes / total if total else 1.0),
        "diffs": diffs,
    }


def measure(ilspycmd: str, original: Path, rebuilt: Path) -> dict:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        orig = load(ilspycmd, original, tmp)
        new = load(ilspycmd, rebuilt, tmp)
    return {
        "original": {"path": str(original), "sha256": orig.sha256},
        "rebuilt": {"path": str(rebuilt), "sha256": new.sha256},
        "scopes": {
            "all": compare(orig, new, lambda _k: True, "strict"),
            "hand_authored": compare(orig, new, lambda k: not is_generated(k), "strict"),
            "normalized": compare(orig, new, lambda k: not is_generated(k), "relaxed"),
            "normalized_all": compare(orig, new, lambda _k: True, "relaxed"),
        },
    }


def summarize(name: str, result: dict) -> None:
    print(f"== {name}")
    for scope, label in (("normalized", "normalized"), ("hand_authored", "hand-authored"),
                         ("normalized_all", "normalized/all"),
                         ("all", "strict/all")):
        s = result["scopes"][scope]
        print(f"   {label:<14} {s['code_matched'] * 100:6.2f}% code matched "
              f"({s['code_bytes_matched']}/{s['code_bytes']} bytes), "
              f"{s['bodies_matched']}/{s['bodies']} bodies, "
              f"{s['bodies_differing']} differ, {s['bodies_missing']} missing, "
              f"{s['bodies_extra']} extra")


def show_method(ilspycmd: str, assemblies: list[str], method: str) -> int:
    """Print normalised IL for one method on both sides, for triage."""
    import difflib
    for name in assemblies:
        original = paths.DATA_MANAGED / name
        rebuilt = paths.REBUILT_DIR / name
        if not original.is_file() or not rebuilt.is_file():
            continue
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            orig = load(ilspycmd, original, tmp)
            new = load(ilspycmd, rebuilt, tmp)
        a = orig.bodies.get(method)
        b = new.bodies.get(method)
        if a is None and b is None:
            continue
        print(f"===== {name}: {method}")
        print(f"  original: {a.code_bytes if a else 0} code bytes"
              f"{'' if a else ' (missing)'}")
        print(f"  rebuilt : {b.code_bytes if b else 0} code bytes"
              f"{'' if b else ' (missing)'}")
        if a and b and a.strict == b.strict:
            print("  identical (strict)")
            continue
        if a and b and a.relaxed == b.relaxed:
            print("  identical after local-slot normalisation (only slot assignment differs)")
            continue
        for line in difflib.unified_diff(
                (a.relaxed if a else "").splitlines(),
                (b.relaxed if b else "").splitlines(),
                "original", "rebuilt", lineterm=""):
            print(f"  {line}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--assembly", action="append", default=None,
                    help="assembly file name to measure (default: all reconstructed)")
    ap.add_argument("--ilspycmd", default=shutil.which("ilspycmd") or "ilspycmd")
    ap.add_argument("--baseline", default=str(paths.REFERENCE_DIR / "code_match_report.json"),
                    help="saved report to compare against; exits non-zero on regression")
    ap.add_argument("--show", default=None, metavar="METHOD",
                    help="print the normalised IL of one method on both sides and exit")
    args = ap.parse_args()

    if not shutil.which(args.ilspycmd) and not Path(args.ilspycmd).exists():
        print(f"error: ilspycmd not found ({args.ilspycmd})", file=sys.stderr)
        return 1

    assemblies = args.assembly or [f"{a}.dll" for a in paths.GAME_ASSEMBLIES]
    paths.MATCH_DIR.mkdir(parents=True, exist_ok=True)

    if args.show:
        return show_method(args.ilspycmd, assemblies, args.show)

    report = {
        "tool": "measure_code.py",
        "ilspycmd": subprocess.run([args.ilspycmd, "--version"],
                                   capture_output=True, text=True).stdout.strip(),
        "assemblies": {},
    }
    failed = False
    combined: dict[str, dict] = {}
    for name in assemblies:
        original = paths.DATA_MANAGED / name
        rebuilt = paths.REBUILT_DIR / name
        if not original.is_file() or not rebuilt.is_file():
            print(f"error: missing original or rebuilt {name}", file=sys.stderr)
            failed = True
            continue
        result = measure(args.ilspycmd, original, rebuilt)
        summarize(name, result)

        stem = Path(name).stem
        (paths.MATCH_DIR / f"{stem}.json").write_text(json.dumps(result, indent=2) + "\n")
        with (paths.MATCH_DIR / f"{stem}-diffs.tsv").open("w") as fh:
            fh.write("status\tmethod\toriginal_code_bytes\n")
            for key, status, size in result["scopes"]["all"]["diffs"]:
                fh.write(f"{status}\t{key}\t{size}\n")

        for scope in ("all", "hand_authored", "normalized", "normalized_all"):
            acc = combined.setdefault(scope, {"code_bytes": 0, "code_bytes_matched": 0,
                                              "bodies": 0, "bodies_matched": 0,
                                              "bodies_differing": 0, "bodies_missing": 0,
                                              "bodies_extra": 0})
            for k in acc:
                acc[k] += result["scopes"][scope][k]

        report["assemblies"][name] = {
            "original_sha256": result["original"]["sha256"],
            "rebuilt_sha256": result["rebuilt"]["sha256"],
            "scopes": {k: {kk: vv for kk, vv in v.items() if kk != "diffs"}
                       for k, v in result["scopes"].items()},
        }

    if combined:
        for scope, acc in combined.items():
            acc["code_matched"] = (acc["code_bytes_matched"] / acc["code_bytes"]
                                   if acc["code_bytes"] else 1.0)
        report["total"] = {"scopes": combined}
        t = combined["normalized"]
        print("== total (both assemblies)")
        print(f"   normalized      {t['code_matched'] * 100:6.2f}% code matched "
              f"({t['code_bytes_matched']}/{t['code_bytes']} bytes), "
              f"{t['bodies_matched']}/{t['bodies']} bodies")
        t = combined["hand_authored"]
        print(f"   hand-authored   {t['code_matched'] * 100:6.2f}% code matched "
              f"({t['code_bytes_matched']}/{t['code_bytes']} bytes), "
              f"{t['bodies_matched']}/{t['bodies']} bodies")

    (paths.MATCH_DIR / "report.json").write_text(json.dumps(report, indent=2) + "\n")

    # Merged worklist across assemblies, for triage.
    with (paths.MATCH_DIR / "differences.tsv").open("w") as fh:
        fh.write("assembly\tstatus\tmethod\toriginal_code_bytes\n")
        for name in assemblies:
            stem = Path(name).stem
            tsv = paths.MATCH_DIR / f"{stem}-diffs.tsv"
            if not tsv.is_file():
                continue
            for line in tsv.read_text().splitlines()[1:]:
                fh.write(f"{name}\t{line}\n")

    print(f"==> reports: {paths.MATCH_DIR}")

    if args.baseline:
        baseline_path = Path(args.baseline)
        if baseline_path.is_file():
            baseline = json.loads(baseline_path.read_text())
            regressions = []
            print()
            print(f"== vs saved baseline ({baseline_path.name})")
            for name, data in sorted(report["assemblies"].items()):
                ref = baseline.get("assemblies", {}).get(name)
                if not ref:
                    print(f"   {name}: not in baseline")
                    continue
                for scope in ("normalized", "hand_authored", "all"):
                    cur = data["scopes"][scope]["code_matched"]
                    old = ref["scopes"][scope]["code_matched"]
                    delta = cur - old
                    flag = "" if delta >= -1e-9 else "  REGRESSION"
                    print(f"   {name} [{scope}]: {cur * 100:.2f}% "
                          f"({delta * 100:+.2f}pp){flag}")
                    if delta < -1e-9:
                        regressions.append((name, scope, old, cur))
            if "total" in report and "total" in baseline:
                for scope in ("normalized", "hand_authored", "all"):
                    cur = report["total"]["scopes"][scope]["code_matched"]
                    old = baseline["total"]["scopes"][scope]["code_matched"]
                    delta = cur - old
                    flag = "" if delta >= -1e-9 else "  REGRESSION"
                    print(f"   total [{scope}]: {cur * 100:.2f}% ({delta * 100:+.2f}pp){flag}")
                    if delta < -1e-9:
                        regressions.append(("total", scope, old, cur))
            if regressions:
                print(f"error: {len(regressions)} regression(s) vs baseline", file=sys.stderr)
                return 1
        else:
            print(f"==> no baseline at {baseline_path} (nothing to compare)")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
