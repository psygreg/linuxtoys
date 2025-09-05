#!/bin/bash
# NAME: Zen Browser
# VERSION: 1.0
# DESCRIPTION: zen_desc
# icon: zenbrowser

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub app.zen_browser.zen