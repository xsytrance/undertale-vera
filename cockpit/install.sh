#!/usr/bin/env bash
# The Underground Cockpit — installer (Phase 1).
# Symlinks the repo's Hyprland config into place. Needs hyprland installed
# first:  sudo apt install -y hyprland hyprpaper
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
HYPR_DIR="$HOME/.config/hypr"

if ! command -v Hyprland >/dev/null 2>&1; then
    echo "Hyprland is not installed. Run:  sudo apt install -y hyprland hyprpaper" >&2
    exit 1
fi

mkdir -p "$HYPR_DIR"
if [ -e "$HYPR_DIR/hyprland.conf" ] && [ ! -L "$HYPR_DIR/hyprland.conf" ]; then
    mv "$HYPR_DIR/hyprland.conf" "$HYPR_DIR/hyprland.conf.pre-cockpit.bak"
    echo "Backed up existing config to hyprland.conf.pre-cockpit.bak"
fi
ln -sfn "$HERE/hyprland.conf" "$HYPR_DIR/hyprland.conf"
chmod +x "$HERE/cockpit-start.sh"

echo "Installed. Log out, pick the 'Hyprland' session on the login screen, log in."
echo "The cockpit auto-launches Ember + Undertale. Super+Shift+M exits back to GDM."
