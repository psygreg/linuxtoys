#!/bin/bash
# NAME: Zen Browser
# VERSION: 1.0
# DESCRIPTION: zen_desc
# icon: zen.svg
# repo: https://zen-browser.app

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub app.zen_browser.zen
