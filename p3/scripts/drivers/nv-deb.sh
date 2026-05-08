#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: debian
# reboot: yes
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
prep_tmp
wget https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb
pkg_fromfile cuda-keyring_1.1-1_all.deb
sleep 1
sudo apt-get update
sleep 1
pkg_install cuda-drivers
sleep 1
initramfs_upd
bootloader_upd
zeninf "$msg036"
