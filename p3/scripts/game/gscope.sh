#!/bin/bash
# name: Gamescope
# version: 1.0
# description: gscope_desc
# icon: gaming.svg
# repo: https://github.com/ValveSoftware/gamescope

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
if command -v rpm-ostree >/dev/null 2>&1 || [ "$ID" == "fedora" ] || [[ "$ID_LIKE" =~ "fedora" ]]; then
    sudo_rq
    rpmfusion_chk
    pkg_install gamescope
elif [ "$ID" == "arch" ] || [ "$ID" == "cachyos" ] || [[ "$ID_LIKE" =~ "arch" ]] || [[ "$ID_LIKE" =~ "archlinux" ]]; then
    sudo_rq
    multilib_chk
    pkg_install gamescope
# debian has to be updated manually :/
elif [ "$ID" == "debian" ]; then
    sudo_rq
    prep_tmp
    wget http://ftp.us.debian.org/debian/pool/contrib/g/gamescope/gamescope_3.16.14-1_amd64.deb
    pkg_fromfile ./gamescope_3.16.14-1_amd64.deb
    rm gamescope_3.16.14-1_amd64.deb
else
    sudo_rq
    pkg_install gamescope
fi
# install flatpak runtime as well
if command -v flatpak >/dev/null 2>&1; then
    pkg_flat org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/23.08 org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/24.08 org.freedesktop.Platform.VulkanLayer.gamescope/x86_64/25.08
fi
