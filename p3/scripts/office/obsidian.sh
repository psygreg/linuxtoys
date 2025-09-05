#!/bin/bash
# NAME: Obsidian
# VERSION: 1.9.10
# DESCRIPTION: obsidian_desc
# icon: obsidian.png

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub md.obsidian.Obsidian