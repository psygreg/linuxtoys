#!/bin/bash
# name: Oversteer
# version: 1.0
# description: oversteer_desc
# icon: oversteer.png
# repo: https://github.com/berarma/oversteer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_flat io.github.berarma.Oversteer
if is_solus; then
    UDEV_RULES_DIR="/usr/lib/udev/rules.d/"
    prep_create "$UDEV_RULES_DIR/99-fanatec-wheel-perms.rules" "$UDEV_RULES_DIR/99-logitech-wheel-perms.rules" "$UDEV_RULES_DIR/99-thrustmaster-wheel-perms.rules"
else
    UDEV_RULES_DIR="/etc/udev/rules.d/"
    prep_create "$UDEV_RULES_DIR/99-fanatec-wheel-perms.rules" "$UDEV_RULES_DIR/99-logitech-wheel-perms.rules" "$UDEV_RULES_DIR/99-thrustmaster-wheel-perms.rules"
fi
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-fanatec-wheel-perms.rules -O "$UDEV_RULES_DIR/99-fanatec-wheel-perms.rules"
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-logitech-wheel-perms.rules -O "$UDEV_RULES_DIR/99-logitech-wheel-perms.rules"
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-thrustmaster-wheel-perms.rules -O "$UDEV_RULES_DIR/99-thrustmaster-wheel-perms.rules"
zeninf "$msg146"
xdg-open https://github.com/berarma/oversteer?tab=readme-ov-file#supported-devices