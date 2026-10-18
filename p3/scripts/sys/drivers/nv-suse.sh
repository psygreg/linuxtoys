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
# NVIDIA dropped Maxwell/Pascal/Volta support in driver 590+; anything below
# Turing must go through the 580 branch instead.
_legacy_gpu_chk () {
    local id legacy=1
    while read -r id; do
        [ -n "$id" ] || continue
        (( $((16#$id)) <= 0x1d )) && legacy=0
    done < <(lspci -n -d 10de: 2>/dev/null | awk '$2 ~ /0300|0302/ { split($3, a, ":"); print substr(a[2], 1, 2) }')
    return $legacy
}
if _legacy_gpu_chk; then
    die "$incompatmsg"
    exit 100
fi
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
