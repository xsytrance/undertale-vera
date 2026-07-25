#!/usr/bin/env bash
# The Underground Cockpit — orchestrator (Phase 1: minimal bring-up).
# Runs as Hyprland's exec-once. Ensures Ember is up, then launches the Ember
# kiosk pane and Undertale. Guided Mode's save watch persists on its own
# (guided_watch.json), so no API call is needed here.
set -u

# The cockpit runs its OWN Ember on loopback (:9093), not the tailnet-facing
# ember-dev (:9092). The authentic skin serves art extracted from this
# machine's game install, and that art must never be served from a shared
# surface — see cockpit/ember-cockpit.service and docs/LOCAL_SKIN_MANIFEST.md.
EMBER_URL="http://127.0.0.1:9093"
EMBER_UNIT="ember-cockpit"
UNDERTALE_APPID=391540

log() { echo "[cockpit] $*" >&2; }

# 1. Ember up (systemd user unit survives reboots; start is a no-op if active)
systemctl --user start "$EMBER_UNIT" 2>/dev/null || true
for _ in $(seq 1 30); do
    curl -sf -o /dev/null "$EMBER_URL/" && break
    sleep 1
done
if ! curl -sf -o /dev/null "$EMBER_URL/"; then
    log "Ember did not come up at $EMBER_URL — launching kiosk anyway (it will retry)."
    log "if this persists:  systemctl --user status $EMBER_UNIT"
else
    # Report the skin so a silent fallback to the original art is visible in
    # the log rather than a mystery on screen.
    skin=$(curl -sf "$EMBER_URL/api/health" | grep -o '"skin":"[a-z]*"' || true)
    log "ember up (${skin:-skin unknown})"
fi

# 2. Ember pane — kiosk window with a stable class for the window rules.
#    Dedicated profile dir so it never fights the normal Chrome session.
google-chrome --app="$EMBER_URL" --class=ember-kiosk \
    --user-data-dir="$HOME/.config/ember-kiosk" \
    --no-first-run --disable-session-crashed-bubble &

# 3. Game pane — launched last so it takes the master (68%) pane.
#    Give the kiosk a moment to map its window first.
sleep 3
steam -silent "steam://rungameid/$UNDERTALE_APPID" &

log "cockpit launched: Ember kiosk + Undertale ($UNDERTALE_APPID)"
