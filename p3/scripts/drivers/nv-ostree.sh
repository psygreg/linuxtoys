#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: ostree
# reboot: ostree
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
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
        sudo rpm-ostree install -yA akmods-keys-0.0.2-8.fc$(rpm -E %fedora).noarch.rpm
        cd ..
        rm -r silverblue-akmods-keys
    fi
fi
sudo rpm-ostree install akmod-nvidia xorg-x11-drv-nvidia-cuda
sudo tee /etc/modprobe.d/blacklist-nouveau-nova.conf <<EOF
blacklist nouveau
blacklist nova_core
EOF
sudo rpm-ostree kargs --append=rd.driver.blacklist=nova_core --append=modprobe.blacklist=nova_core --append=rd.driver.blacklist=nouveau --append=modprobe.blacklist=nouveau --append=nvidia-drm.modeset=1
zenity --info --title="Nvidia Drivers" --text=$"Reboot your system to apply the changes." --width 300 --height 300