#!/bin/bash
# name: btrfs-Assistant
# version: 1.0
# description: btassist_desc
# icon: btassist.svg
# nocontainer
# compat: arch, cachy, fedora, suse, ubuntu, debian

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
    sudo_rq
    if [[ "$ID" =~ "arch" ]] || [[ "$ID" != "cachyos" ]] && [[ "$ID_LIKE" == *arch* ]] || [[ "$ID" != "cachyos" ]] && [[ "$ID_LIKE" == *archlinux* ]]; then
        if zenity --question --text=$"This requires the Chaotic-AUR repository. Do you want to enable it?" --width 360 --height 300; then
            chaotic_aur_lib
        else
            zenwrn $"Skipping btrfs-assistant installation."
        fi
    fi
    _packages=(btrfs-assistant snapper)
    _install_
else
    fatal $"Your root filesystem is not btrfs."
fi