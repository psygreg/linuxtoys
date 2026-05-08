#!/bin/bash
# name: Steam
# version: 1.0
# description: steam_desc
# icon: steam.svg
# repo: https://store.steampowered.com/
# nocontainer: ubuntu, debian, suse, solus

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
if is_fedora || is_ostree; then
    sudo_rq
    rpmfusion_chk
    pkg_install steam steam-devices
elif is_arch || is_cachy; then
    sudo_rq
    multilib_chk
    pkg_install steam steam-devices
else
    # use flatpak for all others, since native install usually only works well on Fedora and Arch
    sudo_rq
    pkg_flat com.valvesoftware.Steam
    pkg_install steam-devices
fi