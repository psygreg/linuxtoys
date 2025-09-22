#!/bin/bash
# name: Realtek WiFi 8821CE
# version: 1.0
# description: rtl8821ce_desc
# icon: rtl.png
# compat: arch, cachyos
# reboot: yes
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
cd $HOME
git clone https://aur.archlinux.org/rtl8821ce-dkms-git.git
sudo_rq
# set up dependencies
_packages=(linux-headers dkms bc base-devel)
_install_
cd rtl8821ce-dkms-git
makepkg -d
sudo pacman --noconfirm -U rtl8821ce-dkms-git-*.tar.zst
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
rm -r rtl8821ce-dkms-git
zeninf "$msg036"
