#!/bin/bash
# name: LACT
# version: 1.0
# description: lact_desc
# icon: device.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
# request sudo - LACT requires system level installation
sudo_rq
flatpak install --or-update --system --noninteractive io.github.ilya_zlobintsev.LACT