#!/bin/bash
# NAME: Google Chrome
# VERSION: 1.0
# DESCRIPTION: chrome_desc
# icon: chrome.svg
# repo: https://chrome.google.com/

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub com.google.Chrome
