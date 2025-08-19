#!/bin/bash
# name: EasyEffects
# version: 1.0
# description: efx_desc
# icon: efx.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
# request sudo, EasyEffects needs to be installed on system level
sudo_rq
flatpak install --or-update --system --noninteractive flathub com.github.wwmm.easyeffects