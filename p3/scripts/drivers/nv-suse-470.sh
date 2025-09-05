#!/bin/bash
# name: Nvidia Drivers (v470)
# version: 1.0
# description: nv_desc_470
# icon: nvidia.svg
# compat: suse
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
REPO_ALIAS="nvidia"
case "$VERSION_ID" in
    *Tumbleweed*) REPO_URL="https://download.nvidia.com/opensuse/tumbleweed" ;;
    15.*) REPO_URL="https://download.nvidia.com/opensuse/leap/$VERSION_ID" ;;
    *)  fatal $"Unsupported OpenSUSE version." ;;
esac
sudo_rq
if ! zypper lr | grep -q "^${REPO_ALIAS}\s"; then
    sudo zypper ar -f "$REPO_URL" "nvidia"
fi
sudo zypper in -y x11-video-nvidiaG05 nvidia-computeG05
sudo dracut -f --regenerate-all
zenity --info --title="Nvidia Drivers" --text=$"Reboot your system to apply the changes." --width 300 --height 300