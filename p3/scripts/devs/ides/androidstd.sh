#!/bin/bash
# name: Android Studio
# version: 1.0
# description: droidstd_desc
# icon: android-studio.svg
# repo: https://developer.android.com/studio/

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --user --or-update --noninteractive flathub com.google.AndroidStudio
zeninf "$msg018"