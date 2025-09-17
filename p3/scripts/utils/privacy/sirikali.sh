#!/bin/bash
# name: SiriKali
# version: 1.0
# description: sirikali_desc
# icon: sirikali.png

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../../libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/../../../libs/lang/${langfile}.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub io.github.mhogomchungu.sirikali
