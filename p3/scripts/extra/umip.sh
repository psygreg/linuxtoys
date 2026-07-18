#!/bin/bash
# name: UMIP Patch
# description: umipp_desc
# icon: terminal.svg
# reboot: yes
# nocontainer
# new

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq

if is_fedora || is_rhel || is_suse ; then
    grubbyargs_upd "clearcpuid=umip"
elif is_ostree; then
    kargs_upd "clearcpuid=umip"
else
    # for systemd-boot
    prep_create /etc/kernel/cmdline.d/10-umip-patch.conf
    echo "clearcpuid=umip" | sudo tee /etc/kernel/cmdline.d/10-umip-patch.conf >/dev/null
    # for GRUB
    prep_create /etc/default/grub.d/10-umip-patch.cfg
    sudo tee /etc/default/grub.d/10-umip-patch.cfg << EOF
GRUB_CMDLINE_LINUX_DEFAULT="\${GRUB_CMDLINE_LINUX_DEFAULT} clearcpuid=umip"
EOF

    bootloader_upd
fi
zeninf "$rebootmsg"