#!/bin/bash
# name: btrfs-Assistant
# version: 1.0
# description: btassist_desc
# icon: btassist.svg
# nocontainer

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
if [ "$(findmnt -n -o FSTYPE /)" = "btrfs" ]; then
    sudo_rq
    if [[ "$ID" =~ "arch" ]] || [[ "$ID" != "cachyos" ]] && [[ "$ID_LIKE" == *arch* ]] || [[ "$ID" != "cachyos" ]] && [[ "$ID_LIKE" == *archlinux* ]]; then
        if zenity --question --text "$msg035" --width 360 --height 300; then
            chaotic_aur_lib
        else
            zenwrn "Skipping btrfs-assistant installation."
        fi
    fi
    _packages=(btrfs-assistant snapper)
    _install_
else
    fatal "$msg220"
fi
