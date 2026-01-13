#!/bin/bash
# name: ProtonUp
# version: 1.0
# description: pup_desc
# icon: pupgui.png
# repo: https://davidotek.github.io/protonup-qt/

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub net.davidotek.pupgui2
