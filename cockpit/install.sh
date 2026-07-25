#!/usr/bin/env bash
# The Underground Cockpit — installer.
# The cockpit is its own login-screen session ("Undertale Cockpit") that runs
# Hyprland with an explicit --config, so the stock Hyprland session and
# ~/.config/hypr stay untouched — and other vera cockpits can coexist.
# Needs hyprland installed first:  sudo apt install -y hyprland hyprpaper
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
SESSION_DIR=/usr/share/wayland-sessions

if ! command -v Hyprland >/dev/null 2>&1; then
    echo "Hyprland is not installed. Run:  sudo apt install -y hyprland hyprpaper" >&2
    exit 1
fi

chmod +x "$HERE/cockpit-start.sh"
Hyprland --verify-config --config "$HERE/hyprland.conf" >/dev/null 2>&1 || {
    echo "hyprland.conf failed to parse — run: Hyprland --verify-config --config $HERE/hyprland.conf" >&2
    exit 1
}

# Clean up the pre-.desktop install layout: a symlink we used to plant at the
# default config path (restoring any backed-up original).
HYPR_CONF="$HOME/.config/hypr/hyprland.conf"
if [ -L "$HYPR_CONF" ] && [ "$(readlink -f "$HYPR_CONF")" = "$HERE/hyprland.conf" ]; then
    rm "$HYPR_CONF"
    [ -e "$HYPR_CONF.pre-cockpit.bak" ] && mv "$HYPR_CONF.pre-cockpit.bak" "$HYPR_CONF"
    echo "Removed old symlink at $HYPR_CONF (stock Hyprland session is vanilla again)."
fi

# The cockpit's own Ember instance: loopback only, authentic skin. Kept
# separate from ember-dev on purpose — that one binds 0.0.0.0 and is reachable
# across the tailnet, and the authentic skin serves art extracted from this
# machine's game install, which must not leave it.
UNIT_DIR="$HOME/.config/systemd/user"
mkdir -p "$UNIT_DIR"
if cmp -s "$HERE/ember-cockpit.service" "$UNIT_DIR/ember-cockpit.service"; then
    echo "Ember cockpit unit already installed and current."
else
    install -m 644 "$HERE/ember-cockpit.service" "$UNIT_DIR/ember-cockpit.service"
    systemctl --user daemon-reload
    echo "Installed ember-cockpit.service (127.0.0.1:9093, authentic skin)."
fi
systemctl --user enable ember-cockpit >/dev/null 2>&1 || true

if [ ! -d "$HERE/../static/assets/local/emblems" ]; then
    echo
    echo "NOTE: no extracted art found — the cockpit will show the original look."
    echo "To use the authentic skin, run from the repo root:"
    echo "    python3 tools/extract_undertale_assets.py && python3 tools/map_local_skin.py"
    echo
fi

# Render the session entry. .desktop Exec= cannot expand $HOME, so the absolute
# path is baked in here rather than committed — that keeps machine-specific
# paths out of the repo (the leak-guard CI job forbids them).
RENDERED="$HERE/.undertale-cockpit.desktop"
sed "s|@COCKPIT_DIR@|$HERE|g" "$HERE/undertale-cockpit.desktop.in" > "$RENDERED"

if [ -f "$SESSION_DIR/undertale-cockpit.desktop" ] \
   && cmp -s "$RENDERED" "$SESSION_DIR/undertale-cockpit.desktop"; then
    echo "Session entry already installed and current."
else
    echo "Config OK. One step needs root — run:"
    echo
    echo "  sudo install -m 644 $RENDERED $SESSION_DIR/undertale-cockpit.desktop"
    echo
fi
echo "Then log out and pick 'Undertale Cockpit' at the login screen."
echo "Super+Shift+M exits the cockpit back to GDM."
