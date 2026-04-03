#!/bin/bash
# name: Extension Manager
# version: 1.0
# description: extman_desc
# icon: extensions.svg
# desktop: gnome
# repo: https://github.com/mjakeman/extension-manager

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_flatpaks=(
    com.mattjakeman.ExtensionManager
)
_flatpak_
zeninf "$msg018"