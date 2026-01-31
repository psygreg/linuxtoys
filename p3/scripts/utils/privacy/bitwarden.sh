#!/bin/bash
# name: Bitwarden
# version: 1.0
# description: bitwarden_desc
# icon: bitwarden.png
# repo: https://www.bitwarden.com/

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.bitwarden.desktop

