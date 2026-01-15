#!/bin/bash
# name: Brave Browser
# version: 1.0
# description: brave_desc
# icon: brave.svg
# repo: https://brave.com

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak_install --or-update --noninteractive flathub com.brave.Browser
zeninf "$msg018"
