#!/bin/bash
# name: Nvidia Drivers (v580)
# description: nv580_desc
# icon: nvidia.svg
# nocontainer
# gpu: Nvidia
# compat: arch, !cachy, fedora, rhel
# reboot: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
if is_arch || is_cachy; then
    pkg_remove nvidia-open nvidia-open-dkms nvidia-open-lts nvidia-settings nvidia-utils
    pkg_install nvidia-580xx-dkms nvidia-580xx-utils nvidia-580xx-settings
    initramfs_upd
    bootloader_upd
    zeninf "$msg036"
elif is_fedora || is_rhel; then
    rpmfusion_chk
    if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
        call_script modsign
    fi
    pkg_remove akmod-nvidia xorg-x11-drv-nvidia-cuda
    pkg_install akmod-nvidia-580xx xorg-x11-drv-nvidia-580xx-cuda
    initramfs_upd
    bootloader_upd
    zeninf "$msg036"
else
    fatal "$msg077"
fi