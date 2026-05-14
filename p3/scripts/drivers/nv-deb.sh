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
debian_ver=$(lsb_release -rs 2>/dev/null)
prep_tmp
pkg_install gcc lsb-release software-properties-common
sudo add-apt-repository contrib
wget "https://developer.download.nvidia.com/compute/cuda/repos/debian$debian_ver/x86_64/cuda-keyring_1.1-1_all.deb"
pkg_fromfile cuda-keyring_1.1-1_all.deb
sleep 1
sudo apt update
sleep 1
pkg_install cuda-drivers
sleep 1
initramfs_upd
bootloader_upd
zeninf "$msg036"
