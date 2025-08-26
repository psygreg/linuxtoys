#!/bin/bash
# name: Bazaar
# version: 1.0
# description: bazaar_desc
# icon: bazaar.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
flatpak_in_lib
sudo flatpak install --or-update --system --noninteractive flathub io.github.kolunmi.Bazaar
zeninf "$msg018"