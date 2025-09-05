#!/bin/bash
# name: Arch-Update
# version: 1.0
# description: archupd_desc
# icon: archup.svg
# compat: arch
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
chaotic_aur_lib
sudo pacman -S --noconfirm arch-update
sleep 1
arch-update --tray --enable
zeninf $"Operations completed."