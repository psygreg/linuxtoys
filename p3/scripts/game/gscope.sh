#!/bin/bash
# name: Gamescope
# version: 1.0
# description: gscope_desc
# icon: gaming.svg

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
if command -v rpm-ostree >/dev/null 2>&1 || [ "$ID" == "fedora" ] || [[ "$ID_LIKE" =~ "fedora" ]]; then
    sudo_rq
    rpmfusion_chk
    _packages=(gamescope)
    _install_
elif [ "$ID" == "arch" ] || [ "$ID" == "cachyos" ] || [[ "$ID_LIKE" =~ "arch" ]] || [[ "$ID_LIKE" =~ "archlinux" ]]; then
    sudo_rq
    multilib_chk
    _packages=(gamescope)
    _install_
# debian has to be updated manually :/
elif [ "$ID" == "debian" ]; then
    sudo_rq
    cd $HOME
    wget http://ftp.us.debian.org/debian/pool/contrib/g/gamescope/gamescope_3.16.14-1_amd64.deb
    sudo apt install ./gamescope_3.16.14-1_amd64.deb
    rm gamescope_3.16.14-1_amd64.deb
else
    sudo_rq
    _packages=(gamescope)
    _install_
fi
# install flatpak runtime as well
if command -v flatpak >/dev/null 2>&1; then
    flatpak_in_lib
    flatpak install --or-update --user --noninteractive flathub org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/23.08 org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/24.08
fi