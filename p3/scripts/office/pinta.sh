#!/bin/bash
# NAME: Pinta
# VERSION: 1.0
# DESCRIPTION: pinta_desc
# icon: pinta

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.github.PintaProject.Pinta