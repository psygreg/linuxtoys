#!/bin/bash
# name: AppArmor
# version: 1.0
# description: aa_desc
# icon: apparmor.png
# compat: debian, arch, cachyos
# reboot: yes
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
_packages=(apparmor)
if is_debian; then
    _packages+=(apparmor-utils)
fi
_install_
# enable and start apparmor
if pacman -Qi grub 2>/dev/null 1>&2 || dpkg -s grub-efi 2>/dev/null 1>&2; then # grub
    echo 'GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT} apparmor=1 security=apparmor"' | sudo tee /etc/default/grub.d/99-apparmor.cfg
    if is_debian; then
        sudo update-grub
    elif is_arch || is_cachyos; then
        sudo grub-mkconfig -o /boot/grub/grub.cfg
    fi
else # systemd-boot
    echo "apparmor=1 security=apparmor" | sudo tee /etc/kernel/cmdline.d/99-apparmor.conf
    sudo bootctl update
fi
sudo systemctl enable apparmor
