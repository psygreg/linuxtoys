#!/bin/bash
# name: Ananicy-cpp
# version: 1.0
# description: ananicy_desc
# icon: optimizer.svg
# compat: arch

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_packages=(ananicy-cpp cachyos-ananicy-rules-git)
_install_
sudo systemctl enable --now ananicy-cpp.service
zeninf "$rebootmsg" # while rebooting is not necessary, it is still recommended.