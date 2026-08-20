#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: debian, !pika, ubuntu
# reboot: yes
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
prep_tmp
if is_debian; then    
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

    debian_ver=$(lsb_release -rs 2>/dev/null || true)
    debian_ver=${debian_ver%%.*}
    case "$debian_ver" in
        12|13)
            ;;
        *)
            # workaround for testing/sid users
            debian_ver="13"
            ;;
    esac

    wget "https://developer.download.nvidia.com/compute/cuda/repos/debian$debian_ver/x86_64/cuda-keyring_1.1-1_all.deb"
    pkg_fromfile cuda-keyring_1.1-1_all.deb
    sudo apt update
    pkg_install nvidia-open
    initramfs_upd
    bootloader_upd
elif is_ubuntu; then 
    sudo apt update
    drv_ver=$(apt-cache search '^nvidia-driver-[0-9]+-open$' | grep -oP 'nvidia-driver-\K[0-9]+(?=-open)' | sort -n | tail -1)
    pkg_install "nvidia-driver-$drv_ver-open"
fi
secureboot_check
zeninf "$msg036"
