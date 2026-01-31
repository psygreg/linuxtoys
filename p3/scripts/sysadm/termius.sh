#!/bin/bash
# name: Termius
# version: 1.0
# description: termius_desc
# icon: termius.png
# repo: https://termius.com/
# compat: debian, ubuntu, fedora, arch, suse

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.termius.Termius
zeninf "$msg018"
