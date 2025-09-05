#!/bin/bash
# name: Oversteer
# version: 1.0
# description: oversteer_desc
# icon: oversteer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub io.github.berarma.Oversteer
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-fanatec-wheel-perms.rules -P /etc/udev/rules.d
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-logitech-wheel-perms.rules -P /etc/udev/rules.d
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-thrustmaster-wheel-perms.rules -P /etc/udev/rules.d
zeninf $"Please check your wheel's compatibility before proceeding."
xdg-open https://github.com/berarma/oversteer?tab=readme-ov-file#supported-devices