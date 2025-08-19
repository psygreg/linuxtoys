#!/bin/bash
# name: ProtonPlus
# version: 1.0
# description: pp_desc
# icon: protonplus

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.vysp3r.ProtonPlus