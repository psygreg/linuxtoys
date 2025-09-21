#!/bin/bash
# name: Input Remapper
# version: 1.0
# description: remapper_desc
# compat: fedora, arch, debian, ubuntu, cachy, ostree
# nocontainer
# reboot: ostree

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
if [ "$ID" == "arch" ] || [ "$ID" == "cachyos" ] || [[ "$ID_LIKE" =~ "arch" ]]; then
    chaotic_aur_lib
    _packages=(input-remapper-git)
else
    _packages=(input-remapper)
fi
_install_
zeninf "$msg018"