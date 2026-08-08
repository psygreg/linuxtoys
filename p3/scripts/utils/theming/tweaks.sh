#!/bin/bash
# name: Gnome Tweaks
# version: 1.0
# description: tweaks_desc
# icon: tweaks.svg
# desktop: gnome
# repo: https://github.com/GNOME/gnome-tweaks

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install gnome-tweaks
zeninf "$msg018"