#!/bin/bash
# name: Protontricks
# version: 1.0
# description: ptricks_desc
# icon: proton.svg
# repo: https://github.com/Matoking/protontricks

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.github.Matoking.protontricks