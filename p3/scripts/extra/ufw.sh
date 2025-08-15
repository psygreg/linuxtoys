#!/bin/bash
# NAME: ufw
# VERSION: 1.0
# DESCRIPTION: ufw_desc
# ICON: help-about
# compat: ubuntu, debian, arch

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
if zenity --question --text "$msg007" --width 360 --height 300; then
    sudo_rq
    _packages=(ufw gufw)
    _install_
    if command -v ufw &> /dev/null; then
        sudo ufw default deny incoming
        sudo ufw default allow outgoing
        sudo ufw enable
    fi
    zeninf "$msg008"
fi
