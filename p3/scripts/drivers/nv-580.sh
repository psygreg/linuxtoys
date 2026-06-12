#!/bin/bash
# name: Nvidia Drivers (v580)
# description: nv580_desc
# icon: nvidia.svg
# nocontainer
# gpu: Nvidia
# compat: debian, arch, !cachy, fedora, rhel
# reboot: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_debian; then
    prep_tmp
    pkg_install gcc lsb-release
    debian_ver=$(lsb_release -rs 2>/dev/null)
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then
        prep_edit /etc/apt/sources.list.d/debian.sources
        sudo sed -i 's/^Components: \(.*\)main$/Components: \1main contrib non-free/' /etc/apt/sources.list.d/debian.sources
    else
        prep_edit /etc/apt/sources.list
        sudo sed -i 's/^deb http:\/\/\([^ ]*\) \([^ ]*\) main$/deb http:\/\/\1 \2 main contrib non-free/' /etc/apt/sources.list
        sudo sed -i 's/^deb-src http:\/\/\([^ ]*\) \([^ ]*\) main$/deb-src http:\/\/\1 \2 main contrib non-free/' /etc/apt/sources.list
    fi
    sudo apt update
    wget "https://developer.download.nvidia.com/compute/cuda/repos/debian${debian_ver:-trixie}/x86_64/cuda-keyring_1.1-1_all.deb"
    pkg_fromfile cuda-keyring_1.1-1_all.deb
    sleep 1
    sudo apt update
    pkg_install nvidia-driver-pinning-580 cuda-drivers-580
    sleep 1
    initramfs_upd
    bootloader_upd
    zeninf "$msg036"
elif is_arch || is_cachy; then
    pkg_install nvidia-580xx-dkms nvidia-580xx-utils nvidia-580xx-settings
    initramfs_upd
    bootloader_upd
    zeninf "$msg036"
elif is_fedora || is_rhel; then
    rpmfusion_chk
    pkg_install akmod-nvidia-580xx xorg-x11-drv-nvidia-580xx-cuda
    initramfs_upd
    bootloader_upd
    zeninf "$msg036"
else
    fatal "$msg077"
fi