#!/bin/bash
# name: Osu!
# version: 1.0
# description: osu_desc
# icon: osu.png
# repo: https://osu.ppy.sh

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub sh.ppy.osu
