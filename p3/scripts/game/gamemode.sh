#!/bin/bash
# name: Gamemode
# version: 1.0
# description: gamemode_desc
# icon: gamemode

# --- Start of the script code ---
if [ "$ID" == "arch" ] || [ "$ID" == "cachyos" ] || [[ "$ID_LIKE" =~ "arch" ]] || [[ "$ID_LIKE" =~ "archlinux" ]]; then
    sudo_rq
    _packages=(gamemode lib32-gamemode)
    _install_
    unset _packages
else
    sudo_rq
    _packages=(gamemode)
    _install_
    unset _packages
fi