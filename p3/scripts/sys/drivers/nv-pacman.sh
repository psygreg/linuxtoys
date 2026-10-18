#!/bin/bash
# name: Nvidia Drivers (Open Modules)
# version: 1.0
# description: nv_rtx_desc
# icon: nvidia.svg
# compat: arch
# reboot: yes
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
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
sudo_rq
pkg_install nvidia-open-dkms nvidia-utils nvidia-settings
initramfs_upd
info "$rebootmsg"
