#!/bin/bash
# name: Kolibri
# version: 1.0
# description: kolibri_desc
# icon: kolibri.png
# repo: https://learningequality.org/kolibri/about-kolibri/

# --- Start of the script code ---
. /etc/os-release
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
flatpak_in_lib
flatpak install --or-update --user --noninteractive flathub org.learningequality.Kolibri