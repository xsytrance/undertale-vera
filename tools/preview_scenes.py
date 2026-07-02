#!/usr/bin/env python3
"""Preview route backdrops behind the REAL UI — the legibility test for scene art.

Scene art is gitignored, so we judge a new set by eye, in situ: load the running
app, read a fixture save so the actual panels + parchment text render, then swap
the backdrop per route and screenshot. Run it after dropping PNGs into
static/assets/scenes/<route>.png — or before, to capture the gradient fallback.
This is the true test (a 4-up grid can't show how a backdrop fights the ink).

Usage:
  # shell 1:  uvicorn undertale_vera_app:app --port 9092
  # shell 2:  python3 tools/preview_scenes.py --base http://127.0.0.1:9092 --out preview/

Honors $UNDERTALE_VERA_CHROMIUM for the browser binary (same as inspector.py).
"""
from __future__ import annotations

import argparse
import os
import sys

ROUTES = ["pacifist", "neutral", "genocide", "undetermined"]
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = os.path.join(HERE, "tests", "fixtures")


def main() -> int:
    ap = argparse.ArgumentParser(description="Screenshot each route backdrop behind the live UI")
    ap.add_argument("--base", default="http://127.0.0.1:9092", help="running app base URL")
    ap.add_argument("--out", default=os.path.join(HERE, "preview"), help="output directory")
    ap.add_argument("--file0", default=os.path.join(FIX, "file0_pacifist"))
    ap.add_argument("--ini", default=os.path.join(FIX, "undertale_pacifist.ini"))
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed: pip install playwright && playwright install chromium",
              file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)
    chromium = os.environ.get("UNDERTALE_VERA_CHROMIUM", "")
    launch = {"executable_path": chromium} if chromium and os.path.exists(chromium) else {}

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch)
        page = browser.new_page(viewport={"width": 1280, "height": 820})
        errs: list[str] = []
        page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        page.goto(args.base, wait_until="networkidle")

        # Read a save so the REAL panels + parchment text render over the backdrop.
        page.set_input_files("#file0-input", args.file0)
        page.set_input_files("#ini-input", args.ini)
        page.click("#upload-btn")
        page.wait_for_selector("#truth-panel:not(.hidden)", timeout=10000)

        scenes = page.evaluate("() => fetch('/api/scenes').then(r=>r.json()).then(d=>d.scenes)")
        for route in ROUTES:
            page.evaluate("(rt) => window.SceneLayer && window.SceneLayer.setRoute(rt)", route)
            page.wait_for_timeout(700)
            out = os.path.join(args.out, f"scene_{route}.png")
            page.screenshot(path=out)
            tag = "ART" if (isinstance(scenes, dict) and route in scenes) else "gradient"
            print(f"wrote {out}  [{tag}]")
        browser.close()
        if errs:
            ignorable = ("ERR_CONNECTION", "font")
            real = [e for e in errs if not any(s in e for s in ignorable)]
            if real:
                print("console errors:", real, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
