#!/bin/bash
# name: Xpadneo
# version: 1.0
# description: xneo_desc
# icon: gaming.svg
# compat: fedora, ubuntu, debian, ostree, suse, arch
# reboot: yes
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
    _packages=(dkms linux-headers-$(uname -r))
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
    _packages=(dkms make bluez bluez-tools kernel-devel kernel-headers)
elif [[ "$ID" =~ "arch" ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
    _packages=(dkms linux-headers bluez bluez-utils)
elif [[ "$ID" =~ "suse" ]] || [[ "$ID_LIKE" =~ *suse* ]]; then
    _packages=(dkms make bluez kernel-devel kernel-source)
fi
_install_
cd $HOME
git clone https://github.com/atar-axis/xpadneo.git
cd xpadneo
sudo ./install.sh
cd ..
rm -r xpadneo
zeninf "$msg036"