#!/bin/bash
# name: Chaotic AUR
# version: 1.0
# description: chaotic_desc
# icon: aur.svg
# compat: arch, cachy

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
chaotic_aur_lib
zeninf $"Operations completed."