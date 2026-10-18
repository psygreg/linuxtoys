#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: fedora, rhel
# reboot: yes
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
rpmfusion_chk
secureboot_check
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
    die "$incompatmsg"$'\n'"Use v580 instead."
    exit 100
fi
if is_rhel && [ "$(rpm -E %rhel)" = "10" ]; then
    pkg_install kernel-devel-matched kernel-headers
    sudo dnf config-manager --add-repo "https://developer.download.nvidia.com/compute/cuda/repos/rhel$(rpm -E %rhel)/$(arch)/cuda-rhel$(rpm -E %rhel).repo"
    sudo dnf clean expire-cache
    sudo dnf makecache
    { lspci | grep -i "nvidia.*rtx" && pkg_install nvidia-open nvidia-container-toolkit; } || pkg_install cuda-drivers nvidia-container-toolkit
else
    pkg_install --allowerasing akmod-nvidia xorg-x11-drv-nvidia-cuda
fi
initramfs_upd
info "$rebootmsg"
