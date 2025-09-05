#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: suse
# reboot: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
REPO_ALIAS="nvidia"
# check if Tumbleweed or Leap
case "$VERSION_ID" in
    *Tumbleweed* | *Slowroll*) REPO_URL="https://download.nvidia.com/opensuse/tumbleweed" ;;
    15.*) REPO_URL="https://download.nvidia.com/opensuse/leap/$VERSION_ID" ;;
    *) fatal $"Unsupported OpenSUSE version." ;;
esac
sudo_rq
if ! zypper lr | grep -q "^${REPO_ALIAS}\s"; then
    sudo zypper ar -f "$REPO_URL" "nvidia"
fi
sudo zypper in -y x11-video-nvidiaG06 nvidia-computeG06
sudo dracut -f --regenerate-all
zenity --info --title="Nvidia Drivers" --text=$"Reboot your system to apply the changes." --width 300 --height 300