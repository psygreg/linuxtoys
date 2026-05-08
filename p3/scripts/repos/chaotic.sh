#!/bin/bash
# name: Chaotic AUR
# version: 1.0
# description: chaotic_desc
# icon: aur.svg
# compat: arch, cachy
# repo: https://aur.chaotic.cx/

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
chaotic_aur_lib
zeninf "$msg018"