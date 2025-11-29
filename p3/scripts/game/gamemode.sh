#!/bin/bash
# name: Gamemode
# version: 1.0
# description: gamemode_desc
# icon: gaming.svg
# compat: fedora, ostree, debian, ubuntu, arch, suse, ublue

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
gamemode_in () {
    sudo_rq
    if [ "$ID" == "arch" ] || [[ "$ID_LIKE" =~ "arch" ]] || [[ "$ID_LIKE" =~ "archlinux" ]]; then
        _packages=(gamemode lib32-gamemode)
    else
        _packages=(gamemode)
    fi
    _install_
}
if [ -f /etc/systemd/system/set-ondemand-governor.service ]; then
    zenity --question --text "$msg295" --height=330 --width=330
    if [ $? -eq 0 ]; then
        gamemode_in
    else
        exit 100
    fi
else
    gamemode_in
fi