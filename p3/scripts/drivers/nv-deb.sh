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
pkg_install gcc lsb-release 
if [ -f /etc/apt/sources.list.d/debian.sources ]; then
    prep_edit /etc/apt/sources.list.d/debian.sources
    sudo sed -i 's/^Components: \(.*\)main$/Components: \1main contrib non-free/' /etc/apt/sources.list.d/debian.sources
else
    prep_edit /etc/apt/sources.list
    sudo sed -i 's/^deb http:\/\/\([^ ]*\) \([^ ]*\) main$/deb http:\/\/\1 \2 main contrib non-free/' /etc/apt/sources.list
    sudo sed -i 's/^deb-src http:\/\/\([^ ]*\) \([^ ]*\) main$/deb-src http:\/\/\1 \2 main contrib non-free/' /etc/apt/sources.list
fi
sudo apt update
debian_ver=$(lsb_release -rs 2>/dev/null)
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
