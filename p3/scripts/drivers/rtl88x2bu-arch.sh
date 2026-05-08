#!/bin/bash
# name: Realtek WiFi RTL88x2BU
# version: 1.0
# description: External RTL88x2BU/RTL8822BU USB WiFi driver with DKMS
# icon: rtl.png
# compat: arch, cachy
# reboot: yes
# nocontainer
# repo: https://github.com/RinCat/RTL88x2BU-Linux-Driver

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq

_kernel_headers_pkg="linux-headers"
case "$(uname -r)" in
    *cachyos-lts*) _kernel_headers_pkg="linux-cachyos-lts-headers" ;;
    *cachyos*) _kernel_headers_pkg="linux-cachyos-headers" ;;
    *hardened*) _kernel_headers_pkg="linux-hardened-headers" ;;
    *zen*) _kernel_headers_pkg="linux-zen-headers" ;;
    *lts*) _kernel_headers_pkg="linux-lts-headers" ;;
esac

pkg_install rtl88x2bu-dkms-git "$_kernel_headers_pkg" dkms bc base-devel

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
