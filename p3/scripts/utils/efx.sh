#!/bin/bash
# name: EasyEffects
# version: 1.0
# description: efx_desc
# icon: efx.svg
# repo: https://github.com/wwmm/easyeffects

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
# request sudo, EasyEffects needs to be installed on system level
sudo_rq
_flatpaks=(
    com.github.wwmm.easyeffects
)
_flatpak_