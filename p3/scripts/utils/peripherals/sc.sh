#!/bin/bash
# name: StreamController
# version: 1.0
# description: sc_desc
# icon: sc.png
# repo: https://github.com/StreamController/StreamController

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub com.core447.StreamController
zeninf "$msg018"
