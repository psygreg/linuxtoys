#!/bin/bash
# name: preemptfedora
# description: preempt_desc
# icon: cpu-x.png
# compat: fedora, ostree, rhel, ubuntu
# nocontainer

# --- Start of the script code ---
askpass
if is_fedora || is_rhel; then
    grubbyargs_upd 'preempt=full'
elif is_ubuntu; then
    prep_create /etc/default/grub.d/10-preempt.cfg
    sudo_ tee /etc/default/grub.d/10-preempt.cfg << EOF
GRUB_CMDLINE_LINUX_DEFAULT="\${GRUB_CMDLINE_LINUX_DEFAULT} preempt=full"
EOF
    bootloader_upd
elif is_ostree; then
    kargs_upd 'preempt=full'
fi

info "$finishmsg"
