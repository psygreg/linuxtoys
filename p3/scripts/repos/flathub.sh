#!/bin/bash
# name: Flathub
# version: 1.0
# description: flat_desc
# icon: flathub.svg
# reboot: yes
# repo: https://flathub.org
# compat: !solus, !fedora, !ostree

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
pkg_flat
zeninf "$msg018"