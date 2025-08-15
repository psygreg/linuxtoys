#!/bin/bash
# name: codecfix
# version: 1.0
# description: codecfix_desc
# icon: help-about
# compat: suse, fedora, ostree

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
. /etc/os-release
if zenity --question --text "$msg080" --width 360 --height 300; then
    if [[ "$ID_LIKE" == *suse* ]]; then
        insta opi
        sudo opi codecs
        zeninf "$msg018"
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
        rpmfusion_chk
        _packages=(libavcodec-freeworld)
        _install_
        zeninf "$msg018"
    else
        zeninf "$msg077"
    fi
fi