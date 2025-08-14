#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia
# compat: ostree
# reboot: ostree

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
# check for rpmfusion repos before proceeding
sudo_rq
rpmfusion_chk
if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
    # enable secure boot support by signing the Nvidia driver modules like in standard Fedora
    if ! rpm -qi "akmods-keys" &>/dev/null; then
        _packages=(rpmdevtools akmods)
        _install_
        sudo kmodgenca
        sudo mokutil --import /etc/pki/akmods/certs/public_key.der
        cd $HOME
        git clone https://github.com/CheariX/silverblue-akmods-keys
        cd silverblue-akmods-keys
        sudo bash setup.sh
        rpm-ostree install -yA akmods-keys-0.0.2-8.fc$(rpm -E %fedora).noarch.rpm
        cd ..
        rm -r silverblue-akmods-keys
    fi
fi
rpm-ostree install akmod-nvidia xorg-x11-drv-nvidia-cuda
sudo rpm-ostree kargs --append=rd.driver.blacklist=nouveau,nova_core --append=modprobe.blacklist=nouveau --append=nvidia-drm.modeset=1
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300