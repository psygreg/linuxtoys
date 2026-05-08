#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
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
pkg_install akmod-nvidia xorg-x11-drv-nvidia-cuda
prep_create /etc/modprobe.d/blacklist-nouveau-nova.conf
sudo tee /etc/modprobe.d/blacklist-nouveau-nova.conf <<EOF
blacklist nouveau
blacklist nova_core
EOF
kargs_upd "rd.driver.blacklist=nova_core" "modprobe.blacklist=nova_core" "rd.driver.blacklist=nouveau" "modprobe.blacklist=nouveau" "nvidia-drm.modeset=1"
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300