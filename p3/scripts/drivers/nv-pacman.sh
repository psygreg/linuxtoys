#!/bin/bash
# name: Nvidia Drivers (Open Modules)
# version: 1.0
# description: nv_rtx_desc
# icon: nvidia.svg
# compat: arch
# reboot: yes
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install nvidia-open-dkms nvidia-utils nvidia-settings
initramfs_upd
bootloader_upd
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300