#!/usr/bin/env python3
"""Parser-expansion engine — promote file0 indices ONLY when the real corpus proves them.

The parser-truth law forbids assigning meaning to a file0 line by guessing. This
tool is the sanctioned, data-driven way to expand coverage: it treats a corpus of
real saves as GROUND TRUTH and proposes a file0 index → meaning only when that
index's value CORROBORATES a documented `undertale.ini [General]` field across the
whole corpus.

Method (per documented [General] field, e.g. Love / Kills / Gold / Time / Room / Fun):
  - For every file0 line index, count the saves where file0[index] == the INI
    field's value (numeric compare, whitespace-tolerant), among saves where both
    sides are present.
  - The best index is a CONFIDENT promotion candidate only at 100% agreement
    across at least `min_saves` saves. Anything below 100% is reported but NOT
    promoted — a single counterexample means the mapping is coincidental or
    version-specific, and we never guess.

This never writes a save and never commits corpus data (saves stay gitignored).
It emits a proposal report; promoting a field into save_parser.FILE0_KNOWN_FIELDS
remains a deliberate human edit, justified by this evidence.

Usage:
  python3 tools/parser_expand.py <corpus_dir>
  python3 tools/parser_expand.py <corpus_dir> --json --min-saves 20
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

# Documented, version-stable [General] keys worth corroborating a file0 index against.
GENERAL_FIELDS = ("love", "kills", "gold", "time", "room", "fun")


def _num(raw: Optional[str]) -> Optional[float]:
    """Whitespace/quote-tolerant numeric parse; None when not a clean number.

    Undertale writes ini values quoted and float-formatted ("69.000000") and pads
    file0 lines with a trailing space ("69 "), so both sides are normalized here.
    """
    if raw is None:
        return None
    try:
        return float(str(raw).strip().strip('"'))
    except (TypeError, ValueError):
        return None


def build_observations(saves: list[dict[str, Optional[str]]]) -> list[dict[str, Any]]:
    """Parse each save into {lines: [float|None], ini: {field: float|None}}."""
    obs: list[dict[str, Any]] = []
    for s in saves:
        parsed = parse_undertale_save(s["file0"], s["ini"])
        lines = [_num(ln) for ln in parsed.file0_lines]
        ini = {f: _num(parsed.ini_get("general", f)) for f in GENERAL_FIELDS}
        obs.append({"name": s["name"], "lines": lines, "ini": ini})
    return obs


def correlate(obs: list[dict[str, Any]], min_saves: int = 10) -> dict[str, Any]:
    """For each [General] field, find the file0 index that best mirrors it.

    Returns, per field: the best index, how many saves corroborated it, how many
    were comparable (both sides present + numeric), the agreement ratio, and
    whether it clears the confident-promotion bar (100% over >= min_saves).
    """
    max_len = max((len(o["lines"]) for o in obs), default=0)
    proposals: dict[str, Any] = {}

    for fld in GENERAL_FIELDS:
        comparable = [o for o in obs if o["ini"].get(fld) is not None]
        best: Optional[dict[str, Any]] = None
        for idx in range(max_len):
            agree = 0
            seen = 0
            for o in comparable:
                if idx >= len(o["lines"]) or o["lines"][idx] is None:
                    continue
                seen += 1
                if o["lines"][idx] == o["ini"][fld]:
                    agree += 1
            if seen == 0:
                continue
            ratio = agree / seen
            cand = {"index": idx, "agree": agree, "seen": seen, "ratio": ratio}
            if best is None or (ratio, seen) > (best["ratio"], best["seen"]):
                best = cand
        if best is not None:
            best["confident"] = best["ratio"] == 1.0 and best["seen"] >= min_saves
        proposals[fld] = best
    return {"saves": len(obs), "min_saves": min_saves, "proposals": proposals}


def format_report(rep: dict[str, Any]) -> str:
    lines = [f"Corpus saves: {rep['saves']}  (confident bar: 100% over >= {rep['min_saves']})", ""]
    for fld, p in rep["proposals"].items():
        if not p:
            lines.append(f"  [General].{fld:<6} → no comparable saves")
            continue
        tag = "PROMOTE" if p.get("confident") else "weak   "
        lines.append(
            f"  {tag} [General].{fld:<6} ↔ file0[{p['index']}]  "
            f"{p['agree']}/{p['seen']} saves agree ({p['ratio']:.0%})"
        )
    lines.append("")
    lines.append("PROMOTE = corroborated 100% across the corpus; safe to document in")
    lines.append("save_parser.FILE0_KNOWN_FIELDS. weak = evidence insufficient; do NOT guess.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Corroborate file0 indices against the real corpus")
    ap.add_argument("root", help="directory of real saves (gitignored corpus)")
    ap.add_argument("--min-saves", type=int, default=10, help="min corroborating saves to call it confident")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if not os.path.isdir(args.root):
        print(f"not a directory: {args.root}", file=sys.stderr)
        return 2
    obs = build_observations(discover_saves(args.root))
    if not obs:
        print("No saves found. Point this at a real corpus directory "
              "(saves stay out of the repo).", file=sys.stderr)
        return 1
    rep = correlate(obs, min_saves=args.min_saves)
    print(json.dumps(rep, indent=2) if args.json else format_report(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
