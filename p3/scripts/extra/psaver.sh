#!/bin/bash
# name: psaver
# version: 1.0
# description: psaver_desc
# icon: power-saver

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/optimizers.lib"
. /etc/os-release
if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    if zenity --question --text "$msg176" --width 360 --height 300; then
        sudo_rq
        psave_lib
    fi
else
    nonfatal "$msg234"
fi