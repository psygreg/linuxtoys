#!/bin/bash
# name: Steam
# version: 1.0
# description: steam_desc

# --- Start of the script code ---
if command -v rpm-ostree >/dev/null 2>&1 || [ "$ID" == "fedora" ] || [[ "$ID_LIKE" =~ "fedora" ]]; then
    sudo_rq
    rpmfusion_chk
    _packages=(steam steam-devices)
    _install_
    unset _packages
elif [ "$ID" == "arch" ] || [ "$ID" == "cachyos" ] || [[ "$ID_LIKE" =~ "arch" ]] || [[ "$ID_LIKE" =~ "archlinux" ]]; then
    sudo_rq
    multilib_chk
    _packages=(steam steam-devices)
    _install_
    unset _packages
else
    # use flatpak for all others, since native install usually only works well on Fedora and Arch
    sudo_rq
    flatpak_in_lib
    flatpak install --or-update --user --noninteractive com.valvesoftware.Steam
    _packages=(steam-devices)
    _install_
    unset _packages
fi