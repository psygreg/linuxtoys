#!/bin/bash
# name: Gnome Tweaks
# version: 1.0
# description: tweaks_desc
# icon: tweaks.svg
# desktop: gnome

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
_packages=(gnome-tweaks)
_install_
zeninf "$msg018"