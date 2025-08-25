#!/bin/bash
# name: Realtek WiFi 8821CE
# version: 1.0
# description: rtl8821ce_desc
# icon: rtl.png
# compat: ubuntu, debian
# reboot: yes
# nocontainer

# --- Start of the script code ---
cd $HOME
git clone https://github.com/tomaspinho/rtl8821ce.git
sudo_rq
# set up dependencies
_packages=(bc module-assistant build-essential dkms)
_install_
# ensure removal of older driver
if dpkg -s rtl8821ce-dkms &>/dev/null; then
    sudo apt remove -y rtl8821ce-dkms
fi
cd rtl8821ce
sudo m-a prepare
sudo ./dkms-install.sh
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