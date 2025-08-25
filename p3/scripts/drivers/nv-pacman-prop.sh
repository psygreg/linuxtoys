#!/bin/bash
# name: Nvidia Drivers (Proprietary)
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: arch
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
sudo_rq
sudo pacman -S nvidia-dkms nvidia-utils nvidia-settings
sudo mkinitcpio -P
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300