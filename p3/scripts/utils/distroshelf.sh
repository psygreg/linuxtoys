#!/bin/bash
# name: Distroshelf
# version: 1.0
# description: distroshelf_desc
# icon: distroshelf.svg
# repo: https://github.com/ranfdev/DistroShelf

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
if is_ubuntu; then
    sudo add-apt-repository ppa:michel-slm/distrobox -y
    sudo apt update
fi
_packages=(podman distrobox)
_install_
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub com.ranfdev.DistroShelf
