#!/bin/bash
# name: dsplitm
# version: 1.0
# description: dsplitm_desc
# icon: help-about
# compat: ubuntu, debian, suse, fedora, arch, cachy

# --- Start of the script code ---
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../libs/optimizers.lib"
. /etc/os-release
if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    if zenity --question --text "$msg042" --width 360 --height 300; then
        dsplitm_lib
    fi
else
    nonfatal "$msg234"
fi