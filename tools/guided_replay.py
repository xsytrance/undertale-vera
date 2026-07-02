#!/usr/bin/env python3
"""Replay a labelled save corpus through Guided Mode — a playthrough as a movie.

Copies each corpus folder's save (oldest→newest) into a watched directory at an
interval, so the Guided watcher sees a whole run happen: the party forming, dark
dollars swinging, Jevil falling — with the pinned party reacting live.

Usage:
  1. In Ember's Guided Mode, watch a scratch dir, e.g.  /tmp/guided-demo
  2. python -m tools.guided_replay --corpus saves/deltarune/chapter1 \
         --dest /tmp/guided-demo --interval 8
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import sys
import time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="dir of numbered save folders")
    ap.add_argument("--dest", required=True, help="the directory Guided Mode watches")
    ap.add_argument("--interval", type=float, default=8.0, help="seconds between saves")
    ap.add_argument("--file", default="filech1_0", help="save filename inside each folder")
    args = ap.parse_args()

    folders = sorted(
        [d for d in glob.glob(os.path.join(args.corpus, "*/"))
         if os.path.exists(os.path.join(d, args.file))],
        key=lambda d: int(re.match(r"(\d+)", os.path.basename(d.rstrip("/"))).group(1))
        if re.match(r"(\d+)", os.path.basename(d.rstrip("/"))) else 0,
    )
    if not folders:
        print("no corpus folders with", args.file, "under", args.corpus)
        return 1
    os.makedirs(args.dest, exist_ok=True)
    print(f"replaying {len(folders)} saves → {args.dest} every {args.interval}s (Ctrl-C to stop)")
    for d in folders:
        label = os.path.basename(d.rstrip("/"))
        shutil.copy(os.path.join(d, args.file), os.path.join(args.dest, args.file))
        ini = os.path.join(d, "dr.ini")
        if os.path.exists(ini):
            shutil.copy(ini, os.path.join(args.dest, "dr.ini"))
        print("  ✦ saved:", label)
        time.sleep(args.interval)
    print("replay complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
