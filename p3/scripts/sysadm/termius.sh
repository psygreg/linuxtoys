#!/bin/bash
# name: Termius
# version: 1.0
# description: termius_desc
# icon: termius.png
# compat: debian, ubuntu, fedora, arch, suse

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.termius.Termius
zeninf "$msg018"
