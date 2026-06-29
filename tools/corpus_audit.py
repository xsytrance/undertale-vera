#!/usr/bin/env python3
"""Corpus audit — run the parser + route detector over a folder of saves.

Turns the ad-hoc verification sweep into a repeatable command (mirrors the FFT
reference's corpus tooling). Point it at any directory of Undertale saves and get
a coverage report: how many parsed cleanly, the derived-route distribution, the
LOVE range, how many came back `undetermined` (the honest "can't tell"), and any
parser warnings / structure issues.

Discovers saves in two layouts:
  - REAL:    a directory containing a file named `file0` (with a sibling
             `undertale.ini` if present). The label is the parent folder's first
             word (e.g. "Pacifist Saves" → "Pacifist").
  - FIXTURE: flat `file0_<name>` files paired with `undertale_<name>.ini` in the
             same directory (the repo's tests/fixtures layout).

Read-only: this never writes a save. It does NOT commit or copy save data — it
just reports. Save corpora stay out of the repo (gitignored).

Usage:
  python3 tools/corpus_audit.py <dir>
  python3 tools/corpus_audit.py <dir> --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from route_detection import detect_route  # noqa: E402
from save_parser import parse_undertale_save  # noqa: E402


def discover_saves(root: str) -> list[dict[str, Optional[str]]]:
    """Find every save under `root`, in either layout. Returns dicts with
    {label, name, file0, ini}."""
    found: list[dict[str, Optional[str]]] = []
    for dirpath, _dirs, files in os.walk(root):
        fileset = set(files)
        # REAL layout: a folder that *is* a save.
        if "file0" in fileset:
            ini = os.path.join(dirpath, "undertale.ini")
            found.append({
                "label": os.path.basename(os.path.dirname(dirpath)).split()[0] or "?"
                if os.path.dirname(dirpath) else "?",
                "name": os.path.basename(dirpath),
                "file0": os.path.join(dirpath, "file0"),
                "ini": ini if os.path.isfile(ini) else None,
            })
        # FIXTURE layout: flat file0_<name> [+ undertale_<name>.ini].
        for f in files:
            if f.startswith("file0_"):
                name = f[len("file0_"):]
                ini = os.path.join(dirpath, f"undertale_{name}.ini")
                found.append({
                    "label": name.split("_")[0],
                    "name": name,
                    "file0": os.path.join(dirpath, f),
                    "ini": ini if os.path.isfile(ini) else None,
                })
    found.sort(key=lambda s: (s["label"] or "", s["name"] or ""))
    return found


def audit(saves: list[dict[str, Optional[str]]]) -> dict[str, Any]:
    """Parse + route every save; return a structured coverage report."""
    rows: list[dict[str, Any]] = []
    warnings = 0
    struct_issues: list[str] = []
    by_label: dict[str, Counter] = {}
    loves: list[int] = []

    for s in saves:
        parsed = parse_undertale_save(s["file0"], s["ini"])
        route = detect_route(parsed)
        if parsed.warnings:
            warnings += 1
        if len(parsed.file0_lines) < 100:
            struct_issues.append(f"{s['name']}: file0 only {len(parsed.file0_lines)} lines")
        if isinstance(parsed.love, int):
            loves.append(parsed.love)
        by_label.setdefault(s["label"] or "?", Counter())[route["route"]] += 1
        rows.append({
            "label": s["label"], "name": s["name"],
            "love": parsed.love, "ini_kills": parsed.ini_get("general", "kills"),
            "route": route["route"], "confidence": route["confidence"],
        })

    return {
        "total": len(rows),
        "parsed_clean": len(rows),  # the parser never crashes; failures would raise
        "with_warnings": warnings,
        "structure_issues": struct_issues,
        "by_label": {k: dict(v) for k, v in by_label.items()},
        "route_totals": dict(Counter(r["route"] for r in rows)),
        "undetermined": sum(1 for r in rows if r["route"] == "undetermined"),
        "love_min": min(loves) if loves else None,
        "love_max": max(loves) if loves else None,
        "rows": rows,
    }


def format_report(rep: dict[str, Any]) -> str:
    lines = [
        f"Saves found:        {rep['total']}",
        f"Parsed (no crash):  {rep['parsed_clean']}/{rep['total']}",
        f"With warnings:      {rep['with_warnings']}",
        f"Structure issues:   {len(rep['structure_issues'])}",
    ]
    for s in rep["structure_issues"][:10]:
        lines.append(f"  ! {s}")
    lines.append("")
    for label, dist in rep["by_label"].items():
        lines.append(f"[{label}]  derived routes: {dist}")
    lines.append("")
    lines.append(f"Route totals:   {rep['route_totals']}")
    lines.append(f"Undetermined:   {rep['undetermined']}  (honest 'can't tell')")
    lines.append(f"LOVE range:     {rep['love_min']}–{rep['love_max']}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit a folder of Undertale saves")
    ap.add_argument("root", help="directory of saves (real or fixture layout)")
    ap.add_argument("--json", action="store_true", help="emit the full report as JSON")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        print(f"not a directory: {args.root}", file=sys.stderr)
        return 2
    rep = audit(discover_saves(args.root))
    print(json.dumps(rep, indent=2) if args.json else format_report(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
