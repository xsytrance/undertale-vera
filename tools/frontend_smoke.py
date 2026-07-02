#!/usr/bin/env python3
"""Frontend smoke test — drives the built UI in a headless browser and fails on any
broken view, dead flow, or console/page error.

The pytest suite only covers the backend (the wall, parsing, endpoints); this is the
front end's merge gate so a chat/Sound-Test/nav/egg regression can't slip through
silently. No live model needed: with the LLM unreachable, chat returns its grounded
deterministic fallback, which is exactly what we assert renders.

Run against a live server:
    SMOKE_BASE=http://127.0.0.1:9092 python tools/frontend_smoke.py
Locally you may need to point at a browser:
    SMOKE_CHROMIUM=/path/to/chrome python tools/frontend_smoke.py
"""
import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("SMOKE_BASE", "http://127.0.0.1:9092")
FIX = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures")
EXE = os.environ.get("SMOKE_CHROMIUM")

fails = []


def check(cond, msg):
    (print("  ok  :", msg) if cond else (fails.append(msg), print("  FAIL:", msg)))


def main():
    with sync_playwright() as p:
        kw = {"args": ["--no-sandbox", "--autoplay-policy=no-user-gesture-required"]}
        if EXE:
            kw["executable_path"] = EXE
        b = p.chromium.launch(**kw)
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        pg.on("console", lambda m: errors.append("console: " + m.text) if m.type == "error" else None)
        pg.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))

        pg.goto(BASE, wait_until="networkidle")
        pg.evaluate("()=>['council','timeline','journal','constellation','chronicle','judgment','reports','soundtest']"
                    ".forEach(k=>localStorage.setItem('uv_seen_'+k,'1'))")  # skip first-time modals

        # ── core shell ──────────────────────────────────────────────────────
        check(pg.evaluate("()=>!!(window.MusicLayer&&window.VoiceLayer&&window.SoundTest&&window.AudioBus)"),
              "audio layers present")
        check(pg.eval_on_selector(".brand-name", "e=>e.textContent") == "Ember", "brand is Ember")
        check(pg.eval_on_selector_all(".chat-empty-cast .ce-face", "els=>els.length") == 9, "welcome cast shows 9")

        # ── read a save (fixture upload) ────────────────────────────────────
        pg.eval_on_selector("#add-save-btn", "el=>el.click()")
        pg.set_input_files("#file0-input", os.path.join(FIX, "file0_pacifist"))
        pg.set_input_files("#ini-input", os.path.join(FIX, "undertale_pacifist.ini"))
        pg.eval_on_selector("#upload-btn", "el=>el.click()")
        pg.wait_for_function("()=>document.querySelector('#route-badge')?.textContent.trim().length>0", timeout=15000)
        check("Pacifist" in pg.eval_on_selector("#route-badge", "e=>e.textContent"), "save loads (Pacifist route)")

        # ── every mode activates ────────────────────────────────────────────
        for view in ["council", "timeline", "journal", "chronicle", "judgment", "reports", "soundtest", "chat"]:
            pg.eval_on_selector("[data-view=" + view + "]", "el=>el.click()")
            pg.wait_for_timeout(220)
            check(pg.evaluate("()=>!!document.querySelector('#view-" + view + ".active')"), "view '" + view + "' activates")

        # ── chat (deterministic fallback reply when no model) ───────────────
        pg.eval_on_selector("#roster .char-card", "el=>el.click()")
        pg.wait_for_timeout(300)
        pg.fill("#chat-input", "hello there")
        pg.eval_on_selector("#send-btn", "el=>el.click()")
        pg.wait_for_function("()=>{const s=[...document.querySelectorAll('#transcript .msg.them .bubble span')].pop();"
                             " return s && s.textContent.trim().length>0;}", timeout=25000)
        check(True, "chat reply renders")

        # ── Sound Test plays a track ────────────────────────────────────────
        pg.eval_on_selector("[data-view=soundtest]", "el=>el.click()")
        pg.wait_for_selector(".st-card")
        pg.eval_on_selector(".st-card[data-id=a-new-save-file]", "el=>el.click()")
        pg.wait_for_timeout(300)
        check(pg.evaluate("()=>window.SoundTest.activeIds().length===1"), "Sound Test plays a track")
        pg.eval_on_selector("[data-view=chat]", "el=>el.click()")

        # ── master mute ─────────────────────────────────────────────────────
        pg.eval_on_selector("#audio-btn", "el=>el.click()")
        pg.wait_for_selector("#audio-menu")
        pg.eval_on_selector("#audio-mute", "el=>el.click()")
        check(pg.evaluate("()=>window.AudioBus.gain()===0"), "master mute zeroes audio")
        pg.eval_on_selector("#audio-mute", "el=>el.click()")

        # ── an easter egg still fires ───────────────────────────────────────
        pg.fill("#chat-input", "spaghetti")
        pg.eval_on_selector("#send-btn", "el=>el.click()")
        pg.wait_for_timeout(400)
        check(pg.eval_on_selector_all(".fall-item", "els=>els.length") > 0, "word-egg fires")

        # ── Deltarune: the Dark World path ──────────────────────────────────
        pg.eval_on_selector("#add-save-btn", "el=>el.click()")
        pg.set_input_files("#file0-input", {
            "name": "filech1_0", "mimeType": "application/octet-stream",
            "buffer": open(os.path.join(FIX, "filech1_0_completed"), "rb").read(),
        })
        pg.eval_on_selector("#upload-btn", "el=>el.click()")
        pg.wait_for_function("()=>document.body.classList.contains('world-dark')", timeout=15000)
        check(True, "deltarune save flips Dark World mode")
        check(pg.evaluate("()=>getComputedStyle(document.body).getPropertyValue('--ember').trim()") == "#b48bf2",
              "accents go Dark World violet")
        pg.wait_for_timeout(500)
        roster = pg.eval_on_selector_all("#roster .char-card", "els=>els.map(e=>e.dataset.name)")
        check("Susie" in roster and "Jevil" in roster and "Papyrus" not in roster,
              "roster seats the Ch1 cast")
        facts = pg.eval_on_selector("#truth-facts", "e=>e.textContent")
        check("Kris" in facts and "Susie" in facts, "rail shows the parsed party")
        # switch back to the Undertale save → the gold returns, the Underground reseats
        pg.evaluate("()=>{const c=[...document.querySelectorAll('.save-card')]"
                    ".find(c=>c.textContent.includes('Pacifist'));c.click();}")
        pg.wait_for_function("()=>!document.body.classList.contains('world-dark')", timeout=10000)
        pg.wait_for_timeout(500)
        back = pg.eval_on_selector_all("#roster .char-card", "els=>els.map(e=>e.dataset.name)")
        check("Papyrus" in back and "Susie" not in back, "switching back restores the Underground")

        check(not errors, "no console/page errors" + ("" if not errors else " -> " + " | ".join(errors[:6])))
        b.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:   # a thrown assertion/timeout is itself a failure
        fails.append("exception: " + repr(exc))
    if fails:
        print("\nSMOKE FAILED (%d):" % len(fails))
        for f in fails:
            print("  -", f)
        sys.exit(1)
    print("\nSMOKE PASSED ✓")
