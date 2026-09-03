#!/bin/bash
# name: dsplitm
# version: 1.0
# description: dsplitm_desc
# icon: utils.svg
# compat: ubuntu, debian, suse, fedora, arch, cachy, rhel, ostree
# reboot: yes
# nocontainer
# optimized-only: yes

# --- Start of the script code ---
askpass

if [ ! -f "$HOME/.local/.autopatch.state" ]; then
    if is_fedora || is_rhel; then
        grubbyargs_upd "split_lock_detect=off"
    elif is_ostree; then
        kargs_upd "split_lock_detect=off"
    else
        prep_create /etc/sysctl.d/99-splitlock.conf
        echo 'kernel.split_lock_mitigate=0' | sudo tee /etc/sysctl.d/99-splitlock.conf >/dev/null
    fi
else
    info "$msg234"
fi

info "$rebootmsg"