#!/bin/bash
# name: AppArmor
# version: 1.0
# description: aa_desc
# icon: apparmor.svg
# repo: https://apparmor.net
# compat: debian, arch, cachy
# reboot: yes
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install apparmor
if is_debian; then
    pkg_install apparmor-utils
fi
# enable and start apparmor
if pacman -Qi grub 2>/dev/null 1>&2 || dpkg -s grub-efi 2>/dev/null 1>&2; then # grub
    prep_create /etc/default/grub.d/99-apparmor.cfg
    echo 'GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT} apparmor=1 security=apparmor"' | sudo tee /etc/default/grub.d/99-apparmor.cfg
    bootloader_upd
else # systemd-boot
    prep_create /etc/kernel/cmdline.d/99-apparmor.conf
    echo "apparmor=1 security=apparmor" | sudo tee /etc/kernel/cmdline.d/99-apparmor.conf
    bootloader_upd
fi
sysd_enable apparmor
zeninf "$msg018"
