#!/bin/bash
# name: Nvidia Drivers (v470)
# version: 1.0
# description: nv_desc_470
# icon: nvidia.svg
# compat: arch
# reboot: yes
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install nvidia-470xx-dkms nvidia-470xx-utils nvidia-470xx-settings
prep_tmp
# set proper DRM mode on systemd
prep_create /etc/modprobe.d/10-nvidia.conf
wget https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/10-nvidia.conf
copy_ 10-nvidia.conf /etc/modprobe.d/
# refresh boot image
initramfs_upd
bootloader_upd
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300