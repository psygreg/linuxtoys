#!/bin/bash
# name: LibreWolf
# version: 1.0
# description: LibreWolf
# icon: librewolf.svg

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub io.gitlab.librewolf-community