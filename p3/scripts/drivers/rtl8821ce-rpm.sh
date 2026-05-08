#!/bin/bash
# name: Realtek WiFi 8821CE
# version: 1.0
# description: rtl8821ce_desc
# icon: rtl.png
# compat: fedora, suse, ostree, ublue
# reboot: yes
# nocontainer
# repo: https://github.com/tomaspinho/rtl8821ce

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
prep_tmp
git clone https://github.com/tomaspinho/rtl8821ce.git
sudo_rq
# set up dependencies
pkg_install dkms make kernel-devel
# ensure removal of older driver
pkg_remove rtl8821ce-dkms
cd rtl8821ce
sudo m-a prepare
sudo ./dkms-install.sh
# blacklist rtw88_8821ce, which is borked
if [ -f /etc/modprobe.d/blacklist.conf ]; then
    prep_edit /etc/modprobe.d/blacklist.conf
    if grep -q "blacklist rtw88_8821ce" /etc/modprobe.d/blacklist.conf; then
        echo "rtw88_8821ce is already blacklisted, skipping..."
    else
        echo "blacklist rtw88_8821ce" | sudo tee -a /etc/modprobe.d/blacklist.conf
    fi
else
    prep_create /etc/modprobe.d/blacklist.conf
    echo "blacklist rtw88_8821ce" | sudo tee /etc/modprobe.d/blacklist.conf
fi
zeninf "$msg036"