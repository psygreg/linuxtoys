#!/bin/bash
# name: Distroshelf
# version: 1.0
# description: distroshelf_desc
# icon: distroshelf.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
_packages=(podman distrobox)
_install_
flatpak_in_lib
flatpak install --or-update --user --noninteractive com.ranfdev.DistroShelf