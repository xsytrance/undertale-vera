# 🎮 The Underground Cockpit — master plan

**Goal:** one cohesive, Undertale-themed cockpit where the game and Ember live
together — a single launch, no babysitting two windows. **100% usable on one
monitor; extra features when a second monitor is present.**

## The reality we design around (Wayland)
On GNOME/Wayland you **cannot embed** one app's window inside another. So we don't
fight it — we **compose**: a dedicated themed tiling session where the backdrop,
gaps, and borders *are* the frame, the game sits in one region, and Ember sits
beside it. Native input goes to whichever pane is focused (controller → game,
keyboard → whichever). It looks and feels like one cockpit without any fragile
embedding/screen-capture hacks.

## Architecture
A dedicated **Hyprland** Wayland session — "Underground Cockpit" — selectable at the
login screen. **Your normal GNOME desktop stays exactly as it is**; this is just a
second session you boot into to play. (Sway is the stability fallback if Hyprland
fights the GPU; Hyprland is chosen for the eye-candy — animations, rounded corners,
soul-glow.)

**GPU note (important):** your monitor is on the **NVIDIA** card. wlroots compositors
on NVIDIA work with driver 595 but need the NVIDIA-Wayland env flags, and it's the
one bring-up risk. Two mitigations, in order of ease:
1. **Plug the monitor into the motherboard's display port (AMD iGPU)** — then the
   compositor runs on AMD (flawless Wayland) while the NVIDIA card still renders games
   via PRIME. Undertale is tiny; even AMD-only is plenty. *Simplest, most robust.*
2. Keep it on NVIDIA and set the NVIDIA-Wayland env. Note: the Hyprland Ubuntu
   26.04 ships (0.53) is on the **aquamarine** backend, not wlroots — the knobs are
   `AQ_DRM_DEVICES` (pin the compositor's card, by stable PCI path — card0/card1
   renumber across reboots on this box), `LIBVA_DRIVER_NAME=nvidia`,
   `__GLX_VENDOR_LIBRARY_NAME=nvidia`, `NVD_BACKEND=direct`, and
   `cursor:no_hardware_cursors = true` in the config. Works, slightly fussier.

## Components
1. **The Frame** — `hyprpaper` paints the Undertale backdrop; soul-red/gold window
   borders; tuned gaps so the backdrop shows through as the frame. Optional decorative
   border art in the gutters.
2. **Game pane** — Undertale (Steam/Proton) auto-launched, tiled + borderless.
3. **Ember pane** — Ember's web UI in a kiosk browser (`chromium --app=` or Firefox
   kiosk) at `http://127.0.0.1:9092`, Guided Mode **auto-watching your save folder**,
   read-aloud on. (Ember's narrow "sidebar" layout is built for a slim column.)
4. **Orchestrator** — `cockpit-start.sh`: ensure `ember-dev` is up → set the Guided
   watch to your save folder via the API → launch the game → launch the Ember kiosk →
   apply the layout. Clean teardown on exit.

## Single-monitor UX (the baseline — 100% usable)
- **Default split:** game ~68% left · Ember ~32% right.
- **Layout modes**, one hotkey / controller button cycles:
  `Full game (Ember hidden)` ⇄ `Split` ⇄ `Full Ember`.
  → full immersion when you want it, Ember one press away.
- Read-aloud auto-speaks every new party line, so you rarely need to look away.

## Dual-monitor extras (when a 2nd screen is plugged in)
- Auto-detected: **game fullscreen on monitor 1, Ember rich/wide on monitor 2.**
- Bonus panels the 2nd screen unlocks: live **Timeline / Constellation**, the
  **session story**, and the **Sound Test** visualizer — the "director's booth."

## Controls
- Focus toggle: `Super+←/→` or a mapped controller button.
- Layout-mode cycle: `Super+Enter`.
- Read-aloud Repeat/Stop: keyboard binding (controller → keystroke via Steam desktop
  config), since the Steam Controller isn't a raw browser gamepad.

## Theming
Undertale font + palette (already in `determination.css`), black field, soul red/gold
borders, decorative frame art in the gutters, Ember skinned to match. The gutters are
the theme.

## Phases
1. **Bring-up** — install Hyprland; validate it boots on this GPU (or move to AMD
   port); get Undertale + Ember tiling side by side (unstyled). *This is the risk gate.*
   **Status (2026-07-18):** kit ready in `cockpit/` (`hyprland.conf` pinned to the
   NVIDIA card with the AMD fallback documented, `cockpit-start.sh`, `install.sh`,
   `undertale-cockpit.desktop`). Hyprland 0.53.3 installed; nested smoke test passed
   (split + rules verified; Chrome's URL-derived Wayland class handled). The cockpit
   is its own login session — `start-hyprland -- --config <repo path>` — so
   `~/.config/hypr` stays untouched and future vera cockpits coexist as separate
   login entries. Waiting on: the one sudo step `install.sh` prints, then a
   logout → "Undertale Cockpit" test (the real NVIDIA/KMS gate).
2. **Orchestrator** — one command launches game + Ember + auto-watch + read-aloud.
3. **Theming** — backdrop frame, borders, fonts, soul motif.
4. **1-monitor UX** — the 3 layout modes + controller/keyboard focus.
5. **2-monitor extras** — auto-detect 2nd output, spread + bonus panels.
6. **One-click launcher** — `.desktop` + login session entry + docs.

## Open risks
- NVIDIA + wlroots bring-up (mitigated above).
- Kiosk browser choice for `:9092` (chromium `--app` vs Firefox kiosk vs GNOME Web).
- Steam launching cleanly under Hyprland (well-trodden; expected fine).
