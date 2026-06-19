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
if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
    call_script modsign
fi
if is_rhel && [ "$(rpm -E %rhel)" = "10" ]; then
    pkg_install kernel-devel-matched kernel-headers
    sudo dnf config-manager --add-repo "https://developer.download.nvidia.com/compute/cuda/repos/rhel$(rpm -E %rhel)/$(arch)/cuda-rhel$(rpm -E %rhel).repo"
    sudo dnf clean expire-cache
    sudo dnf makecache
    { lspci | grep -i "nvidia.*rtx" && pkg_install nvidia-open nvidia-container-toolkit; } || pkg_install cuda-drivers nvidia-container-toolkit
else
    pkg_install akmod-nvidia xorg-x11-drv-nvidia-cuda
fi
initramfs_upd
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300