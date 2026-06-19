#!/bin/bash
# name: Flathub
# version: 1.0
# description: flat_desc
# icon: flathub.svg
# reboot: yes
# repo: https://flathub.org
# compat: !solus, !fedora, !ostree
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
flatpak_in_lib
zeninf "$msg018"