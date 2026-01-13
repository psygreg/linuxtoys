#!/bin/bash
# NAME: Pinta
# VERSION: 1.0
# DESCRIPTION: pinta_desc
# icon: pinta.svg
# repo: https://www.pinta-project.com

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub com.github.PintaProject.Pinta
