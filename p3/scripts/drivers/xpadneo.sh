#!/bin/bash
# name: Xpadneo
# version: 1.0
# description: xneo_desc
# icon: gaming.svg
# compat: fedora, ubuntu, debian, ostree, suse, arch
# reboot: yes
# nocontainer
# repo: https://github.com/atar-axis/xpadneo

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_debian || is_ubuntu; then
    pkg_install dkms linux-headers-$(uname -r)
elif is_fedora; then
    pkg_install dkms make bluez bluez-tools kernel-devel kernel-headers
elif is_arch; then
    pkg_install dkms linux-headers bluez bluez-utils
elif is_suse; then
    pkg_install dkms make bluez kernel-devel kernel-source
fi
prep_tmp
git clone https://github.com/atar-axis/xpadneo.git
cd xpadneo
sudo ./install.sh
zeninf "$msg036"