#!/bin/bash
# name: Kalzium
# version: 1.0
# description: kalzium_desc
# icon: kalzium.png
# repo: https://apps.kde.org/kalzium/

# --- Start of the script code ---
. /etc/os-release
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.kde.kalzium