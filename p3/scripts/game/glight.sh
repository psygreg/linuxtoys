#!/bin/bash
# name: Greenlight
# version: 1.0
# description: glight_desc
# icon: greenlight.png
# repo: https://github.com/unknownskl/greenlight

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub io.github.unknownskl.greenlight