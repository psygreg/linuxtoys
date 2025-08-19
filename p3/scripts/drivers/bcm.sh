#!/bin/bash
# name: Broadcom WiFi
# version: 1.0
# description: bcm_desc
# icon: bcm.png
# compat: fedora, ostree, ublue, arch, cachy
# reboot: yes
# nocontainer

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
if [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
    rpmfusion_chk
    if command -v rpm-ostree &>/dev/null; then
        sudo rpm-ostree install akmod-wl
    else
        sudo dnf install akmod-wl -y
    fi
elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
    sudo pacman -S --noconfirm linux-headers broadcom-wl-dkms
fi
zeninf "$msg036"