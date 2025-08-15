#!/bin/bash
# name: Waydroid
# version: 1.0
# description: waydroid_desc
# icon: waydroid
# compat: fedora, ostree, debian, ubuntu, arch, cachy, ublue

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
if [ "$XDG_SESSION_TYPE" = "wayland" ]; then
    sudo_rq
    if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
        sudo apt install -y curl ca-certificates
        curl -s https://repo.waydro.id | sudo bash
        sleep 1
    fi
    _packages=(waydroid)
    _install_
    sudo systemctl enable --now waydroid-container
else
    fatal "$msg219"
    exit 1
fi