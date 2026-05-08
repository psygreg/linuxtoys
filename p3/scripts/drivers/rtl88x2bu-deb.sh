#!/bin/bash
# name: Realtek WiFi RTL88x2BU
# version: 1.0
# description: External RTL88x2BU/RTL8822BU USB WiFi driver with DKMS
# icon: rtl.png
# compat: ubuntu, debian
# reboot: yes
# nocontainer
# repo: https://github.com/RinCat/RTL88x2BU-Linux-Driver

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install bc git dkms module-assistant build-essential linux-headers-$(uname -r)

prep_tmp
if command -v m-a &>/dev/null; then
    sudo m-a prepare
fi

git clone https://github.com/RinCat/RTL88x2BU-Linux-Driver.git rtl88x2bu-git
cd rtl88x2bu-git || fatal "Failed to access RTL88x2BU-Linux-Driver sources"

prep_dir /usr/src
prep_rm -rf /usr/src/rtl88x2bu-git
copy_ -rT . /usr/src/rtl88x2bu-git
sudo sed -i 's/PACKAGE_VERSION="@PKGVER@"/PACKAGE_VERSION="git"/g' /usr/src/rtl88x2bu-git/dkms.conf
sudo dkms remove -m rtl88x2bu -v git --all 2>/dev/null || true
sudo dkms add -m rtl88x2bu -v git
sudo dkms autoinstall

if [ -f /etc/modprobe.d/rtw8822bu.conf ]; then
    if grep -q "blacklist rtw88_8822bu" /etc/modprobe.d/rtw8822bu.conf; then
        echo "rtw88_8822bu is already blacklisted, skipping..."
    else
        prep_edit /etc/modprobe.d/rtw8822bu.conf
        echo "blacklist rtw88_8822bu" | sudo tee -a /etc/modprobe.d/rtw8822bu.conf >/dev/null
    fi
else
    prep_create /etc/modprobe.d/rtw8822bu.conf
    echo "blacklist rtw88_8822bu" | sudo tee /etc/modprobe.d/rtw8822bu.conf >/dev/null
fi

zeninf "$msg036"
