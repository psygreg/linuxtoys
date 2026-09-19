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
case "$ID" in
    opensuse-tumbleweed|opensuse-slowroll) REPO_URL="https://download.nvidia.com/opensuse/tumbleweed" ;;
    opensuse-leap) REPO_URL='https://download.nvidia.com/opensuse/leap/$releasever' ;;
    *) die "Unsupported OpenSUSE variant: $ID" ;;
esac
sudo_rq
if ! zypper lr | grep -q "^nvidia\s"; then
    sudo zypper ar -f "$REPO_URL" "nvidia"
fi
pkg_install nvidia-open-driver-G07-signed-kmp-default nvidia-userspace-meta-G07
initramfs_upd
bootloader_upd
zeninf "$msg036"