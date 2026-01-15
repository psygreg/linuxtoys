#!/bin/bash
# name: HTTPie
# version: 1.0
# description: httpie_desc
# icon: httpie.svg
# repo: https://httpie.io/desktop

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub io.httpie.Httpie
zeninf "$msg018"
