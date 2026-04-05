#!/bin/bash
# name: Oversteer
# version: 1.0
# description: oversteer_desc
# icon: oversteer.png
# repo: https://github.com/berarma/oversteer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
_flatpaks=(
    io.github.berarma.Oversteer
)
_flatpak_
if is_solus; then
    UDEV_RULES_DIR="/usr/lib/udev/rules.d/"
else
    UDEV_RULES_DIR="/etc/udev/rules.d/"
fi
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-fanatec-wheel-perms.rules -P "$UDEV_RULES_DIR"
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-logitech-wheel-perms.rules -P "$UDEV_RULES_DIR"
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-thrustmaster-wheel-perms.rules -P "$UDEV_RULES_DIR"
zeninf "$msg146"
xdg-open https://github.com/berarma/oversteer?tab=readme-ov-file#supported-devices