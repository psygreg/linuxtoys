#!/bin/bash
# name: about
# version: 1.0
# description: about_desc
# icon: about.png
# noconfirm: yes

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"
zenity --info --title "LinuxToys" --text "$msg125" --height=300 --width=300