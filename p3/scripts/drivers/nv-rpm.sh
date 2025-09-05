#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: fedora
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
# check rpmfusion
rpmfusion_chk
sudo dnf install -y akmod-nvidia xorg-x11-drv-nvidia-cuda
sudo dracut -f --regenerate-all
zenity --info --title="Nvidia Drivers" --text=$"Reboot your system to apply the changes." --width 300 --height 300