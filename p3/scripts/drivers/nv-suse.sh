#!/bin/bash
# name: Nvidia Drivers
# version: 1.0
# description: nv_desc
# icon: nvidia.svg
# compat: suse
# reboot: yes
# nocontainer
# gpu: Nvidia

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
case "$VERSION_ID" in
    *Tumbleweed* | *Slowroll*) REPO_URL="https://download.nvidia.com/opensuse/tumbleweed" ;;
    15.*) REPO_URL="https://download.nvidia.com/opensuse/leap/$VERSION_ID" ;;
    *) fatal "Unsupported OpenSUSE version." ;;
esac
sudo_rq
if ! zypper lr | grep -q "^nvidia\s"; then
    sudo zypper ar -f "$REPO_URL" "nvidia"
fi
pkg_install nvidia-open-driver-G07-signed-kmp-default nvidia-userspace-meta-G07
initramfs_upd
zeninf "$msg036"