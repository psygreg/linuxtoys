#!/bin/bash
# name: Gamemode
# version: 1.0
# description: gamemode_desc
# icon: gamemode

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
if [ "$ID" == "arch" ] || [ "$ID" == "cachyos" ] || [[ "$ID_LIKE" =~ "arch" ]] || [[ "$ID_LIKE" =~ "archlinux" ]]; then
    sudo_rq
    _packages=(gamemode lib32-gamemode)
    _install_
else
    sudo_rq
    _packages=(gamemode)
    _install_
fi