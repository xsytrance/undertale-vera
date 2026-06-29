#!/usr/bin/env python3
"""Flag-mining engine — find route-discriminative undertale.ini flags from a corpus.

The ini analog of tools/parser_expand.py. Undertale stores hundreds of plot flags
([Toriel] TK, [Papyrus] PK, [Flowey] truename, ...). This treats a route-labelled
corpus as GROUND TRUTH and surfaces which flags cleanly separate routes — e.g. a
kill flag that is SET in Genocide saves and never on a single no-kill Pacifist run.

Method:
  - Group saves by their corpus label (the route folder name).
  - For each (section, key) flag, compute the fraction of each label's saves where
    the flag is SET (present and non-zero).
  - A flag is DISCRIMINATIVE for label L when it is set in >= `min_present` of L's
    saves and in <= `max_other` of every other label's saves. 100%/0% is the
    cleanest possible separator.

This is evidence-gathering, not a runtime dependency: route_detection.py hard-codes
a conservative KILL_FLAGS allow-list justified by what this tool (and community
docs) confirm. It never writes a save and never commits corpus data.

Usage:
  python3 tools/flag_mine.py <corpus_dir>
  python3 tools/flag_mine.py <corpus_dir> --min-present 0.5 --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from save_parser import parse_undertale_save  # noqa: E402
from tools.corpus_audit import discover_saves  # noqa: E402

# [General] bookkeeping keys that aren't plot flags — skip them in the report.
_SKIP_GENERAL = {"name", "love", "time", "room", "roomname", "kills", "fun"}


def _is_set(raw: str) -> bool:
    """A flag is 'set' when present and non-zero (numeric) — or any non-numeric text."""
    try:
        return float(str(raw).strip().strip('"')) != 0.0
    except (TypeError, ValueError):
        return True


def build_rows(saves: list[dict[str, Optional[str]]]) -> list[dict[str, Any]]:
    """Parse each save into {label, flags: set[(section, key)] that are SET}."""
    rows: list[dict[str, Any]] = []
    for s in saves:
        parsed = parse_undertale_save(s["file0"], s["ini"])
        flags = set()
        for section, kv in parsed.ini_sections.items():
            for key, val in kv.items():
                if section == "general" and key in _SKIP_GENERAL:
                    continue
                if _is_set(val):
                    flags.add((section, key))
        rows.append({"label": s["label"] or "?", "flags": flags})
    return rows


def mine(rows: list[dict[str, Any]], min_present: float = 0.5,
         max_other: float = 0.0) -> dict[str, Any]:
    """Score every flag's per-label set-rate and tag discriminative ones (pure)."""
    labels = sorted({r["label"] for r in rows})
    counts = {l: sum(1 for r in rows if r["label"] == l) for l in labels}
    all_flags = sorted({f for r in rows for f in r["flags"]})

    results = []
    for flag in all_flags:
        per_label = {}
        for l in labels:
            total = counts[l] or 1
            setn = sum(1 for r in rows if r["label"] == l and flag in r["flags"])
            per_label[l] = {"set": setn, "total": counts[l], "frac": setn / total}
        # Discriminative for L if set >= min_present in L and <= max_other elsewhere.
        disc_for = None
        for l in labels:
            if per_label[l]["frac"] >= min_present and all(
                    per_label[o]["frac"] <= max_other for o in labels if o != l):
                disc_for = l
                break
        results.append({"section": flag[0], "key": flag[1],
                        "per_label": per_label, "discriminative_for": disc_for})
    # Most cleanly-separating first.
    results.sort(key=lambda r: (r["discriminative_for"] is None,
                                -max(v["frac"] for v in r["per_label"].values())))
    return {"labels": labels, "counts": counts, "flags": results}


def format_report(rep: dict[str, Any]) -> str:
    lines = [f"Labels: {rep['counts']}", "", "Discriminative flags (set in one route, ~absent in the others):"]
    any_disc = False
    for r in rep["flags"]:
        if not r["discriminative_for"]:
            continue
        any_disc = True
        spread = "  ".join(f"{l}={v['set']}/{v['total']}" for l, v in r["per_label"].items())
        lines.append(f"  [{r['section']}] {r['key']:<10} → {r['discriminative_for']:<9} ({spread})")
    if not any_disc:
        lines.append("  (none cleared the thresholds)")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Mine route-discriminative ini flags from a corpus")
    ap.add_argument("root", help="directory of route-labelled saves (gitignored corpus)")
    ap.add_argument("--min-present", type=float, default=0.5, help="min set-rate within the owning route")
    ap.add_argument("--max-other", type=float, default=0.0, help="max set-rate allowed in other routes")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        print(f"not a directory: {args.root}", file=sys.stderr)
        return 2
    rows = build_rows(discover_saves(args.root))
    if not rows:
        print("No saves found. Point this at a real route-labelled corpus.", file=sys.stderr)
        return 1
    rep = mine(rows, min_present=args.min_present, max_other=args.max_other)
    print(json.dumps(rep, indent=2) if args.json else format_report(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
