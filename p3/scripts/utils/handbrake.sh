#!/bin/bash
# name: HandBrake
# version: 1.0
# description: hndbrk_desc
# icon: handbrake.svg
# repo: https://handbrake.fr

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub fr.handbrake.ghb
