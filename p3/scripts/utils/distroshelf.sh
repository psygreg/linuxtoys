#!/bin/bash
# name: Distroshelf
# version: 1.0
# description: distroshelf_desc
# icon: distroshelf.svg
# repo: https://github.com/ranfdev/DistroShelf

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
sudo_rq
if is_ubuntu; then
    sudo add-apt-repository ppa:michel-slm/distrobox -y
    sudo apt update
fi
pkg_install podman distrobox
pkg_flat com.ranfdev.DistroShelf
zeninf "$msg018"
