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
# NVIDIA dropped Maxwell/Pascal/Volta support in driver 590+; anything below
# Turing must go through the 580 branch instead.
_legacy_gpu_chk () {
    local id legacy=1
    while read -r id; do
        [ -n "$id" ] || continue
        (( $((16#$id)) <= 0x1d )) && legacy=0
    done < <(lspci -n -d 10de: 2>/dev/null | awk '$2 ~ /0300|0302/ { split($3, a, ":"); print substr(a[2], 1, 2) }')
    return $legacy
}
if _legacy_gpu_chk; then
    die "$incompatmsg"
    exit 100
fi
# check for rpmfusion repos before proceeding
sudo_rq
rpmfusion_chk
secureboot_check
pkg_install akmod-nvidia xorg-x11-drv-nvidia-cuda
prep_create /etc/modprobe.d/blacklist-nouveau-nova.conf
sudo tee /etc/modprobe.d/blacklist-nouveau-nova.conf <<EOF
blacklist nouveau
blacklist nova_core
EOF
kargs_upd "rd.driver.blacklist=nova_core" "modprobe.blacklist=nova_core" "rd.driver.blacklist=nouveau" "modprobe.blacklist=nouveau" "nvidia-drm.modeset=1"
info "$rebootmsg"
