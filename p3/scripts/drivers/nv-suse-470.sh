#!/bin/bash
# name: Nvidia Drivers (v470)
# version: 1.0
# description: nv_desc_470
# icon: nvidia.svg
# compat: suse
# reboot: yes
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
REPO_ALIAS="nvidia"
case "$VERSION_ID" in
    *Tumbleweed*) REPO_URL="https://download.nvidia.com/opensuse/tumbleweed" ;;
    15.*) REPO_URL="https://download.nvidia.com/opensuse/leap/$VERSION_ID" ;;
    *)  fatal "Unsupported OpenSUSE version." ;;
esac
sudo_rq
if ! zypper lr | grep -q "^${REPO_ALIAS}\s"; then
    sudo zypper ar -f "$REPO_URL" "nvidia"
fi
pkg_install x11-video-nvidiaG05 nvidia-computeG05
initramfs_upd
zenity --info --title "Nvidia Drivers" --text "$msg036" --width 300 --height 300