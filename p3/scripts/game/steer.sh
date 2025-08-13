#!/bin/bash
# name: Oversteer
# version: 1.0
# description: oversteer_desc

# --- Start of the script code ---
sudo_rq
flatpak_in_lib
flatpak install --or-update --user --noninteractive io.github.berarma.Oversteer
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-fanatec-wheel-perms.rules -P /etc/udev/rules.d
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-logitech-wheel-perms.rules -P /etc/udev/rules.d
sudo wget https://github.com/berarma/oversteer/raw/refs/heads/master/data/udev/99-thrustmaster-wheel-perms.rules -P /etc/udev/rules.d
zeninf "$msg146"
xdg-open https://github.com/berarma/oversteer?tab=readme-ov-file#supported-devices