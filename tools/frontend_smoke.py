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
        # Suppress the first-run power picker auto-open — the smoke drives the
        # modal deliberately via the chip instead.
        pg.add_init_script("try{localStorage.setItem('uv_power_seen','1')}catch(e){}")
        errors = []
        def _console(m):
            if m.type != "error":
                return
            url = (m.location or {}).get("url", "") if hasattr(m, "location") else ""
            if "/api/guided/watch" in url:
                return   # the smoke intentionally posts a bad path (expected 400)
            errors.append("console: " + m.text + (" @ " + url if url else ""))
        pg.on("console", _console)
        pg.on("pageerror", lambda e: errors.append("pageerror: " + str(e)))

        pg.goto(BASE, wait_until="networkidle")
        pg.evaluate("()=>['council','timeline','journal','constellation','chronicle','judgment','reports','soundtest']"
                    ".forEach(k=>localStorage.setItem('uv_seen_'+k,'1'))")  # skip first-time modals

        # ── core shell ──────────────────────────────────────────────────────
        check(pg.evaluate("()=>!!(window.MusicLayer&&window.VoiceLayer&&window.SoundTest&&window.AudioBus)"),
              "audio layers present")
        check(pg.eval_on_selector(".brand-name", "e=>e.textContent") == "Ember", "brand is Ember")
        check(pg.eval_on_selector_all(".chat-empty-cast .ce-face", "els=>els.length") == 9, "welcome cast shows 9")

        # ── "START HERE" pointer: shown iff the shelf is empty ──────────────
        agree = pg.evaluate("()=>{const empty=!document.querySelector('#shelf .save-card');"
                            "const tag=!!document.getElementById('start-here-tag');return empty===tag;}")
        check(agree, "start-here tag tracks the empty shelf")

        # ── read a save (fixture upload) ────────────────────────────────────
        pg.eval_on_selector("#add-save-btn", "el=>el.click()")
        pg.set_input_files("#file0-input", os.path.join(FIX, "file0_pacifist"))
        pg.set_input_files("#ini-input", os.path.join(FIX, "undertale_pacifist.ini"))
        pg.eval_on_selector("#upload-btn", "el=>el.click()")
        pg.wait_for_function("()=>document.querySelector('#route-badge')?.textContent.trim().length>0", timeout=15000)
        check("Pacifist" in pg.eval_on_selector("#route-badge", "e=>e.textContent"), "save loads (Pacifist route)")
        check(pg.evaluate("()=>!document.getElementById('start-here-tag')"
                          "&&!document.querySelector('.start-glow')"),
              "start-here pointer retires once a save exists")

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
        check(pg.eval_on_selector_all(".st-group-darkcast .st-card", "els=>els.length") == 9,
              "Sound Test has the Dark World section (bed + 8 Darkners)")
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

        # ── Guided Mode: view + ask bar render; bad watch path rejected ─────
        pg.eval_on_selector("[data-view=guided]", "el=>el.click()")
        pg.wait_for_timeout(250)
        check(pg.evaluate("()=>!!document.querySelector('#view-guided.active')"), "guided view activates")
        check(pg.evaluate("()=>!!(document.getElementById('g-whatnow')&&document.getElementById('g-spoiler'))"),
              "guided ask bar present")
        pg.fill("#guided-path", "/definitely/not/a/dir")
        pg.eval_on_selector("#guided-watch-btn", "el=>el.click()")
        pg.wait_for_timeout(400)
        check("Couldn't watch" in pg.eval_on_selector("#guided-status", "e=>e.textContent"),
              "bad watch path rejected gracefully")

        # ── Power picker: chip + modal + three rungs of the ladder ──────────
        check(pg.evaluate("()=>!!document.getElementById('power-btn')"), "power chip present")
        pg.eval_on_selector("#power-btn", "el=>el.click()")
        pg.wait_for_timeout(250)
        check(pg.evaluate("()=>!document.getElementById('power-modal').classList.contains('hidden')"),
              "power modal opens")
        check(pg.evaluate("()=>document.querySelectorAll('.power-card').length===3"),
              "three power cards render")
        pg.eval_on_selector(".power-card[data-source=openrouter]", "el=>el.click()")
        pg.wait_for_timeout(150)
        check(pg.evaluate("()=>!document.getElementById('power-or').classList.contains('hidden')"
                          "&&document.querySelectorAll('#power-model option').length>=4"),
              "openrouter card reveals key + model suggestions")
        pg.eval_on_selector("#power-cancel", "el=>el.click()")
        pg.wait_for_timeout(150)
        check(pg.evaluate("()=>document.getElementById('power-modal').classList.contains('hidden')"),
              "power modal closes without saving")

        # ── ♿ Vision panel: opens, toggles persist as html classes ──────────
        check(pg.evaluate("()=>!!document.getElementById('vision-btn')"), "vision button present")
        pg.eval_on_selector("#vision-btn", "el=>el.click()")
        pg.wait_for_timeout(200)
        check(pg.evaluate("()=>!document.getElementById('vision-modal').classList.contains('hidden')"),
              "vision panel opens")
        pg.eval_on_selector("#vision-modal [data-a11y=large]", "el=>el.click()")
        pg.wait_for_timeout(150)
        check(pg.evaluate("()=>document.documentElement.classList.contains('a11y-large')"
                          "&&JSON.parse(localStorage.getItem('uv_a11y')).includes('large')"),
              "larger-text toggle applies and persists")
        pg.eval_on_selector("#vision-modal [data-a11y=large]", "el=>el.click()")
        pg.eval_on_selector("#vision-close", "el=>el.click()")
        pg.wait_for_timeout(150)
        check(pg.evaluate("()=>document.getElementById('vision-modal').classList.contains('hidden')"),
              "vision panel closes")

        # ── MultiVera: the introduction renders with the family ─────────────
        pg.eval_on_selector("[data-view=multivera]", "el=>el.click()")
        pg.wait_for_timeout(300)
        check(pg.evaluate("()=>!!document.querySelector('#view-multivera.active')"), "multivera view activates")
        check(pg.evaluate("()=>document.querySelectorAll('#view-multivera .mv-card').length===3"),
              "the vera family renders (Ember / FFT / MGS)")

        # ── The Prompt Workshop: live prompt + instructions render ──────────
        pg.eval_on_selector("[data-view=workshop]", "el=>el.click()")
        pg.wait_for_timeout(400)
        check(pg.evaluate("()=>!!document.querySelector('#view-workshop.active')"), "workshop view activates")
        pg.wait_for_function("()=>document.getElementById('ws-example').textContent.includes('HARD FACTS')", timeout=8000)
        check(True, "live example prompt loads from /api/workshop")
        check(pg.evaluate("()=>document.querySelectorAll('#ws-instructions .ws-card').length>=6"),
              "feature instruction cards render")
        check(pg.evaluate("()=>document.querySelectorAll('#view-workshop .ws-prompt').length>=20"),
              "the Suno prompt library renders")

        # ── Credits: the dedicated page renders the hero credit ─────────────
        pg.eval_on_selector("[data-view=credits]", "el=>el.click()")
        pg.wait_for_timeout(250)
        check(pg.evaluate("()=>!!document.querySelector('#view-credits.active')"), "credits view activates")
        check(pg.evaluate("()=>!!document.querySelector('#view-credits .cm-hero-credit')"),
              "hero credit (HylianAngel + NICKISBAD) lives on the credits page")

        # ── The Commons + How It Works render ───────────────────────────────
        pg.eval_on_selector("[data-view=commons]", "el=>el.click()")
        pg.wait_for_timeout(300)
        check(pg.evaluate("()=>!!document.querySelector('#view-commons.active')"), "commons view activates")
        check(pg.evaluate("()=>document.querySelectorAll('.cm-table').length===2"), "field-map tables render")
        pg.eval_on_selector("[data-view=howitworks]", "el=>el.click()")
        pg.wait_for_timeout(250)
        check(pg.evaluate("()=>document.querySelectorAll('#view-howitworks .hiw-layer').length===5"), "how-it-works layers render")

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
