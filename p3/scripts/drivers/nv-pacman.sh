#!/bin/bash
# name: Nvidia Drivers (Open Modules)
# version: 1.0
# description: nv_rtx_desc
# icon: nvidia.svg
# compat: arch
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
sudo_rq
sudo pacman -S nvidia-open-dkms nvidia-utils nvidia-settings
sudo mkinitcpio -P
zenity --info --title="Nvidia Drivers" --text=$"Reboot your system to apply the changes." --width 300 --height 300