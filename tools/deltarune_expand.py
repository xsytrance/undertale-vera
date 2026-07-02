#!/usr/bin/env python3
"""Deltarune parser-expansion evidence tool.

Mirrors tools/parser_expand.py's philosophy for the Deltarune side: field meaning is
PROMOTED with corpus evidence, never guessed. Point it at a directory of labelled
save folders (each containing filech1_0 and ideally dr.ini) and it reports:

  1. layout stability   — field counts across the corpus
  2. dr.ini correlation — file lines that equal dr.ini's Name/Room/Time in EVERY save
  3. variance map       — which lines change at all (candidates for meaning)
  4. partition flags    — given --pre/--post folder-number ranges, lines constant in
                          each group but different between them (true state flags;
                          how line 559 = jevil_state was found: --pre 1-27 --post 28-41)

Usage:
  python -m tools.deltarune_expand --corpus saves/deltarune/chapter1
  python -m tools.deltarune_expand --corpus saves/deltarune/chapter1 --pre 1-27 --post 28-41
"""
from __future__ import annotations

import argparse
import configparser
import glob
import os
import re
import sys


def _folders(corpus: str) -> list[str]:
    out = [d.rstrip("/") for d in glob.glob(os.path.join(corpus, "*/"))
           if os.path.exists(os.path.join(d, "filech1_0"))]
    return sorted(out, key=lambda d: int(re.match(r"(\d+)", os.path.basename(d)).group(1))
                  if re.match(r"(\d+)", os.path.basename(d)) else 0)


def _lines(d: str) -> list[str]:
    return open(os.path.join(d, "filech1_0"), encoding="utf-8", errors="replace").read().split("\n")


def _ini(d: str) -> dict[str, str]:
    p = os.path.join(d, "dr.ini")
    if not os.path.exists(p):
        return {}
    cp = configparser.ConfigParser()
    try:
        cp.read(p)
    except configparser.Error:
        return {}
    return {k: v.strip('"') for k, v in cp["G0"].items()} if "G0" in cp else {}


def _num(d: str) -> int:
    m = re.match(r"(\d+)", os.path.basename(d))
    return int(m.group(1)) if m else 0


def _parse_range(spec: str) -> set[int]:
    a, _, b = spec.partition("-")
    return set(range(int(a), int(b or a) + 1))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--pre", help="folder-number range, e.g. 1-27")
    ap.add_argument("--post", help="folder-number range, e.g. 28-41")
    args = ap.parse_args()

    folders = _folders(args.corpus)
    if not folders:
        print("no labelled save folders found under", args.corpus)
        return 1
    L = {d: _lines(d) for d in folders}
    counts = {len(v) for v in L.values()}
    print(f"corpus: {len(folders)} saves; field counts: {sorted(counts)}")
    N = min(counts)

    # dr.ini correlation
    def match(key: str) -> list[int]:
        hits = []
        for i in range(N):
            ok, seen = True, 0
            for d in folders:
                ini_v = _ini(d).get(key)
                if ini_v is None:
                    continue
                seen += 1
                try:
                    if int(float(ini_v)) != int(float(L[d][i].strip() or "x")):
                        ok = False
                        break
                except ValueError:
                    ok = False
                    break
            if ok and seen >= 2:
                hits.append(i + 1)
        return hits

    for key in ("room", "time"):
        print(f"lines equal to dr.ini {key} in every save: {match(key)}")
    name_hits = [i + 1 for i in range(min(N, 50))
                 if all(L[d][i].strip() == _ini(d).get("name") for d in folders if _ini(d).get("name"))]
    print(f"lines equal to dr.ini Name in every save (first 50 checked): {name_hits}")

    variant = [i + 1 for i in range(N) if len({L[d][i].strip() for d in folders}) > 1]
    print(f"variant lines: {len(variant)} (first 20: {variant[:20]})")

    if args.pre and args.post:
        pre = [d for d in folders if _num(d) in _parse_range(args.pre)]
        post = [d for d in folders if _num(d) in _parse_range(args.post)]
        flags = []
        for i in range(N):
            pv = {L[d][i].strip() for d in pre}
            qv = {L[d][i].strip() for d in post}
            if len(pv) == 1 and len(qv) == 1 and pv != qv:
                flags.append((i + 1, pv.pop(), qv.pop()))
        print(f"partition flags ({args.pre} vs {args.post}): {len(flags)}")
        for i, a, b in flags[:20]:
            print(f"  line {i}: {a!r} → {b!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
