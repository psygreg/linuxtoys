#!/bin/bash
# name: Nvidia Drivers (v470)
# version: 1.0
# description: nv_desc_470
# icon: nvidia.svg
# compat: ostree
# reboot: ostree
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
# check for rpmfusion repos before proceeding
sudo_rq
rpmfusion_chk
if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
    # enable secure boot support by signing the Nvidia driver modules like in standard Fedora
    if ! rpm -qi "akmods-keys" &>/dev/null; then
        pkg_install rpmdevtools akmods
        sudo kmodgenca
        sudo mokutil --import /etc/pki/akmods/certs/public_key.der
        prep_tmp
        git clone https://github.com/CheariX/silverblue-akmods-keys
        cd silverblue-akmods-keys
        sudo bash setup.sh
        pkg_fromfile akmods-keys-0.0.2-8.fc$(rpm -E %fedora).noarch.rpm
    fi
fi
pkg_install xorg-x11-drv-nvidia-470xx akmod-nvidia-470xx xorg-x11-drv-nvidia-470xx-cuda

kargs_upd "rd.driver.blacklist=nouveau,nova_core" "modprobe.blacklist=nouveau" "nvidia-drm.modeset=1"
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300