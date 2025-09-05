#!/bin/bash
# name: VSCodium
# version: 1.0
# description: codium_desc
# icon: vscodium.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --user --or-update --noninteractive flathub com.vscodium.codium
zeninf $"Operations completed."