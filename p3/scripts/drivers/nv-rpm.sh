#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: fedora
# reboot: yes
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
# check rpmfusion
rpmfusion_chk
pkg_install akmod-nvidia xorg-x11-drv-nvidia-cuda
initramfs_upd
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300