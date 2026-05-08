#!/bin/bash
# name: Gamemode
# version: 1.0
# description: gamemode_desc
# icon: gaming.svg
# compat: fedora, ostree, debian, ubuntu, arch, suse, ublue

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
gamemode_in () {
    sudo_rq
    if is_arch; then
        pkg_install gamemode lib32-gamemode
    elif is_solus; then
        pkg_install gamemode gamemode-32bit
    else
        pkg_install gamemode
    fi
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