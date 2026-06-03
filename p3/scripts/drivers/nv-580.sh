#!/bin/bash
# name: Nvidia Drivers (v580)
# description: nv580_desc
# icon: nvidia.svg
# nocontainer
# gpu: Nvidia
# compat: debian, arch, cachy, fedora, rhel
# reboot: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_debian; then
    debian_ver=$(lsb_release -rs 2>/dev/null)
    prep_tmp
    pkg_install gcc lsb-release software-properties-common
    sudo add-apt-repository contrib
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