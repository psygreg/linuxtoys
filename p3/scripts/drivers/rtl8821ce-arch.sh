#!/bin/bash
# name: Realtek WiFi 8821CE
# version: 1.0
# description: rtl8821ce_desc
# icon: rtl.png
# compat: arch, cachy
# reboot: yes
# nocontainer
# repo: https://github.com/tomaspinho/rtl8821ce

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
# set up dependencies
pkg_install rtl8821ce-dkms-git linux-headers dkms bc base-devel
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
