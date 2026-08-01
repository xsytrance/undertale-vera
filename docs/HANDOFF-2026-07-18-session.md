# Session handover — 2026-07-18 (read this first next session)

Context for the next session. The owner restarted their PC mid-session. Everything
below is set up to survive the reboot.

## ✅ Survives the reboot (verified)
- **Services auto-start** (systemd user units, linger on):
  - `ember-dev` → undertale-vera on **http://127.0.0.1:9092** (also tailnet `100.96.211.44:9092`).
  - `fft-psx-vera` → **http://100.96.211.44:7900** (see that repo's own handoff).
- **Guided Mode is already watching the save folder** (persisted in `guided_watch.json`),
  and the owner's run **"xsy" (LOVE 1, Pacifist) is adopted as project 120**.
- Ollama (root service) serves llama3.1:8b on Prime for the in-voice reactions.

## 🎮 Undertale is running (finally) — how it got there
Long GPU saga. Final working setup:
- **Native Steam** (the Snap Steam was removed — its Mesa-only sandbox couldn't use the
  NVIDIA driver → Vulkan `INCOMPATIBLE_DRIVER` → every game crashed).
- Undertale runs via **Proton Experimental** (the native Linux build is a 32-bit binary
  missing `libssl.so.1.0.0` and won't run on Ubuntu 26.04).
- **Save path** (Proton prefix — NOT `~/.config/UNDERTALE`):
  `~/.local/share/Steam/steamapps/compatdata/391540/pfx/drive_c/users/steamuser/AppData/Local/UNDERTALE`
- Hardware: hybrid **AMD iGPU (card2) + NVIDIA RTX 5060 Ti (card1, Blackwell)**; the
  **monitor is on the NVIDIA card**; **GNOME + Wayland**; driver 595.71.05.

**To resume play:** open `http://127.0.0.1:9092` → 🧭 Guided Mode (it's already watching)
→ pick a party (Toriel + Sans) → play Undertale, save at Save Points → beats + in-voice
reactions land. Toggle 🔊 Read aloud for the local **Kokoro** voice (works on Prime).

## 🕯 IN PROGRESS: "The Underground Cockpit" (the current big ask)
Full plan in **`docs/COCKPIT_PLAN.md`**. Owner wants the game + Ember composed into one
Undertale-themed cockpit (no more babysitting two windows). Decisions locked:
- **Full cockpit session** direction (dedicated Hyprland session, not staying in GNOME).
- **100% usable on 1 monitor** (game/Ember split with a Full-game⇄Split⇄Full-Ember
  toggle); **2-monitor gets extras** (game on one screen, Ember "director's booth" on the other).
- **Not started.** Phase 1 (the risk gate) = install Hyprland, confirm it boots on this
  NVIDIA display, get Undertale + Ember tiling side by side.
- **Key shortcut to offer:** move the monitor cable to the motherboard's AMD port →
  wlroots/Hyprland runs flawlessly on AMD (NVIDIA still renders games via PRIME).
  Undertale is light enough it doesn't need the NVIDIA card at all.
- Open question at handoff: start Phase 1? and AMD-port vs keep-NVIDIA.

## ⌨️ Owner's R key is dead (affects how they type)
Their keyboard is an **8BitDo Retro Mechanical Keyboard** (wireless via 2.4GHz receiver).
The **R key produces nothing** — their messages drop every "r". Diagnosed: **no OS-level
remap** (plain `us` layout, no keyd/input-remapper/xmodmap), so it's the keyboard itself:
likely an **onboard firmware remap** (8BitDo stores mappings on-device — reset via 8BitDo
Ultimate Software), a **flaky 2.4GHz link** (try wired USB-C), or a **dead switch**.
Offered but not yet done: a `keyd` stopgap remapping a spare key → R (needs sudo).
**When reading their messages, mentally restore missing r's.**

## What shipped earlier this session (already committed + pushed to main)
- **undertale-vera:** Guided-Mode read-aloud (TTS) — Kokoro server voice + browser
  fallback, per-character voices, key/gamepad bindings. Branch merged to `main` (`2d2373a`).
  Docs: `docs/GUIDED_MODE.md`. Setup: `tools/setup_tts.sh` (`.venv-tts` py3.11 + `models/tts/`).
- **fft-psx-vera:** Kokoro as the default voice + `:7900` tailnet deploy. See that repo's
  `docs/HANDOFF-2026-07-18-kokoro-deploy.md` (has an OPEN bug: campfire CSP blocks CDN scripts).

## Next actions (when the owner returns)
1. Confirm Undertale + Guided Mode still working after reboot (project 120 "xsy").
2. Decide/start the **Cockpit Phase 1** (Hyprland bring-up; AMD-port vs NVIDIA).
3. Optionally fix the R key (8BitDo reset / wired test / keyd stopgap).
