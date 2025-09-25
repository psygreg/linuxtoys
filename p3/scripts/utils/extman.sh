#!/bin/bash
# name: Extension Manager
# version: 1.0
# description: extman_desc
# icon: extensions.svg
# desktop: gnome

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub com.mattjakeman.ExtensionManager
zeninf "$msg018"