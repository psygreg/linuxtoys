#!/bin/bash
# name: Insomnia
# version: 1.0
# description: insomnia_desc
# icon: insomnia.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
flatpak_in_lib
flatpak install --user --or-update --noninteractive flathub rest.insomnia.Insomnia
zeninf $"Operations completed."