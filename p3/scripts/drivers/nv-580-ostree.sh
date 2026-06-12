#!/bin/bash
# name: Nvidia Drivers (v580)
# description: nv580_desc
# icon: nvidia.svg
# nocontainer
# gpu: Nvidia
# compat: ostree
# reboot: yes

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
        pkg_fromfile --ostreecheck akmods-keys-0.0.2-8.fc$(rpm -E %fedora).noarch.rpm
    fi
fi
pkg_install akmod-nvidia-580xx xorg-x11-drv-nvidia-580xx-cuda
prep_create /etc/modprobe.d/blacklist-nouveau-nova.conf
sudo tee /etc/modprobe.d/blacklist-nouveau-nova.conf <<EOF
blacklist nouveau
blacklist nova_core
EOF
kargs_upd "rd.driver.blacklist=nova_core" "modprobe.blacklist=nova_core" "rd.driver.blacklist=nouveau" "modprobe.blacklist=nouveau" "nvidia-drm.modeset=1"
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300