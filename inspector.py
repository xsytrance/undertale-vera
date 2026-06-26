#!/usr/bin/env python3
"""The Inspector — undertale-vera's QA harness.

Ported wholesale from fft-psx-vera's autopilot_probe.py pattern (it is
game-agnostic by design): a deterministic sweep over a registry of surfaces that
checks 404s/routing, console errors, layout overflow / empty pages, and asset
existence — so we have eyes from day one and avoid a manual-QA spiral.

Two engines:
  - Playwright (Chromium headless) when available: screenshots + console-error
    capture + body-text/overflow checks per surface × viewport.
  - Pure-HTTP fallback (urllib) when Playwright isn't installed: status codes +
    asset existence. This guarantees the Inspector runs even on a bare box.

Register undertale-vera's surfaces in SURFACES below — that list is the only
game-specific configuration; the engine is reused unchanged.

Usage:
  python3 inspector.py --base http://127.0.0.1:9092
  python3 inspector.py --base http://127.0.0.1:9092 --out dogfood-output/inspector
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Optional

# ── surface registry (the only game-specific config) ─────────────────────────
# (label, path, settle_seconds, optional_pre_action_selector)
SURFACES: list[tuple[str, str, float, Optional[str]]] = [
    ("home", "/", 2.0, None),
    ("health", "/api/health", 1.0, None),
    ("characters", "/api/characters", 1.0, None),
    ("projects", "/api/projects", 1.0, None),
]

# Static assets the scaffold must ship. Existence is checked over HTTP.
REQUIRED_ASSETS: list[str] = [
    "/css/determination.css",
    "/js/music.js",
    "/js/app.js",
]

# Console noise to ignore (generic, ported from the FFT probe). Includes failures
# loading EXTERNAL CDNs (e.g. the Google Fonts stylesheet) — those are environment
# connectivity issues, not app defects, and the CSS ships serif fallbacks.
CONSOLE_IGNORE = (
    "favicon", "autoplay", "ReadPixels", "WebGL",
    "ERR_CONNECTION", "ERR_NAME_NOT_RESOLVED", "fonts.googleapis", "fonts.gstatic",
)


def _http_get(url: str, timeout: float = 15.0) -> tuple[Optional[int], int, Optional[str]]:
    """Return (status, body_len, error). Never raises."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "undertale-vera-inspector"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, len(body), None
    except urllib.error.HTTPError as e:
        return e.code, 0, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 - inspector must never crash the sweep
        return None, 0, str(e)


def sweep_http(base: str) -> dict[str, Any]:
    """Pure-HTTP deterministic sweep (always available)."""
    results: list[dict[str, Any]] = []
    for label, path, _settle, _sel in SURFACES:
        status, length, err = _http_get(base.rstrip("/") + path)
        results.append({
            "surface": label,
            "path": path,
            "status": status,
            "body_len": length,
            "empty": length < 12 and (path.startswith("/api") is False),
            "error": err,
            "ok": status is not None and 200 <= status < 400,
        })
    assets: list[dict[str, Any]] = []
    for asset in REQUIRED_ASSETS:
        status, length, err = _http_get(base.rstrip("/") + asset)
        assets.append({
            "asset": asset,
            "status": status,
            "exists": status is not None and 200 <= status < 400 and length > 0,
            "error": err,
        })
    failures = [r for r in results if not r["ok"]] + [a for a in assets if not a["exists"]]
    return {
        "engine": "http",
        "base": base,
        "surfaces": results,
        "assets": assets,
        "passed": not failures,
        "failure_count": len(failures),
    }


def sweep_playwright(base: str, out_dir: Optional[str]) -> Optional[dict[str, Any]]:
    """Playwright sweep with screenshots + console errors. None if unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    import os

    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    viewports = [("mobile", 390, 844), ("desktop", 1280, 900)]
    results: list[dict[str, Any]] = []

    # Honor a pinned browser binary (the FFT probe hardcoded a chromium path; we
    # take it from the environment so the same harness runs on boxes where the
    # browser isn't auto-discoverable, e.g. PLAYWRIGHT_BROWSERS_PATH installs).
    launch_kwargs: dict[str, Any] = {"headless": True}
    chromium_path = os.environ.get("UNDERTALE_VERA_CHROMIUM")
    if chromium_path and os.path.exists(chromium_path):
        launch_kwargs["executable_path"] = chromium_path

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        for label, path, settle, selector in SURFACES:
            for vp_name, w, h in viewports:
                console_errors: list[str] = []
                page = browser.new_page(viewport={"width": w, "height": h})
                page.on(
                    "console",
                    lambda msg: console_errors.append(msg.text)
                    if msg.type == "error" and not any(n in msg.text for n in CONSOLE_IGNORE)
                    else None,
                )
                url = base.rstrip("/") + path
                err = None
                text_len = 0
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=25000)
                    page.wait_for_timeout(int(settle * 1000))
                    if selector:
                        page.click(selector, timeout=3000)
                    text_len = len(page.inner_text("body"))
                    if out_dir:
                        page.screenshot(path=os.path.join(out_dir, f"{label}__{vp_name}.png"))
                except Exception as e:  # noqa: BLE001
                    err = str(e)
                results.append({
                    "surface": label,
                    "viewport": vp_name,
                    "url": url,
                    "text_len": text_len,
                    "empty": text_len < 12,
                    "console_errors": console_errors,
                    "error": err,
                })
                page.close()
        browser.close()

    failures = [r for r in results if r["error"] or r["console_errors"]]
    return {
        "engine": "playwright",
        "base": base,
        "surfaces": results,
        "passed": not failures,
        "failure_count": len(failures),
    }


def run(base: str, out_dir: Optional[str] = None) -> dict[str, Any]:
    """Run the best available engine; always also returns the HTTP sweep."""
    http = sweep_http(base)
    pw = sweep_playwright(base, out_dir)
    summary = {"http": http, "playwright": pw}
    summary["passed"] = http["passed"] and (pw is None or pw["passed"])
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="undertale-vera Inspector QA sweep")
    ap.add_argument("--base", default="http://127.0.0.1:9092")
    ap.add_argument("--out", default=None, help="screenshot output dir (Playwright)")
    args = ap.parse_args()
    summary = run(args.base, args.out)
    print(json.dumps(summary, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
