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
    call_script modsign
fi
pkg_install akmod-nvidia xorg-x11-drv-nvidia-cuda
prep_create /etc/modprobe.d/blacklist-nouveau-nova.conf
sudo tee /etc/modprobe.d/blacklist-nouveau-nova.conf <<EOF
blacklist nouveau
blacklist nova_core
EOF
kargs_upd "rd.driver.blacklist=nova_core" "modprobe.blacklist=nova_core" "rd.driver.blacklist=nouveau" "modprobe.blacklist=nouveau" "nvidia-drm.modeset=1"
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300