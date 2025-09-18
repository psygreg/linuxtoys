#!/bin/bash
# name: Realtek WiFi 8821CE
# version: 1.0
# description: rtl8821ce_desc
# icon: rtl.png
# compat: fedora, suse, ostree, ublue
# reboot: yes
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
cd $HOME
git clone https://github.com/tomaspinho/rtl8821ce.git
sudo_rq
# set up dependencies
_packages=(dkms make kernel-devel)
_install_
# ensure removal of older driver
if rpm -qi rtl8821ce-dkms &>/dev/null; then
    if [ "$ID" == "fedora" ] || [[ $ID_LIKE == *fedora* ]]; then
        sudo dnf remove -y rtl8821ce-dkms
    elif [ "$ID" == "suse" ] || [[ $ID_LIKE == *suse* ]]; then
        sudo zypper remove -y rtl8821ce-dkms
    fi
fi
cd rtl8821ce
sudo m-a prepare
sudo ./dkms-install.sh
# blacklist rtw88_8821ce, which is borked
if [ -f /etc/modprobe.d/blacklist.conf ]; then
    if grep -q "blacklist rtw88_8821ce" /etc/modprobe.d/blacklist.conf; then
        echo "rtw88_8821ce is already blacklisted, skipping..."
    else
        echo "blacklist rtw88_8821ce" | sudo tee -a /etc/modprobe.d/blacklist.conf
    fi
else
    echo "blacklist rtw88_8821ce" | sudo tee /etc/modprobe.d/blacklist.conf
fi
cd ..
rm -r rtl8821ce
zeninf "$msg036"