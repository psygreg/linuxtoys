#!/bin/bash
# name: Gamemode
# version: 1.0
# description: gamemode_desc
# icon: gaming.svg
# compat: fedora, ostree, debian, ubuntu, arch, suse, ublue

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"

askpass

if is_arch; then
    multilib_chk
    pkg_install gamemode lib32-gamemode
elif is_solus; then
    pkg_install gamemode gamemode-32bit
else
    pkg_install gamemode
fi

info "$finishmsg"