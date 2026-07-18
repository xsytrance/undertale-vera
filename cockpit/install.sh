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

if [ -f "$SESSION_DIR/undertale-cockpit.desktop" ] \
   && cmp -s "$HERE/undertale-cockpit.desktop" "$SESSION_DIR/undertale-cockpit.desktop"; then
    echo "Session entry already installed and current."
else
    echo "Config OK. One step needs root — run:"
    echo
    echo "  sudo install -m 644 $HERE/undertale-cockpit.desktop $SESSION_DIR/"
    echo
fi
echo "Then log out and pick 'Undertale Cockpit' at the login screen."
echo "Super+Shift+M exits the cockpit back to GDM."
