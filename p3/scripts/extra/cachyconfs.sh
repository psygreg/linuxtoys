#!/bin/bash
# name: cachyconfs
# version: 1.0
# description: cachyconfs_desc
# icon: cachyos.svg
# compat: ubuntu, debian, fedora, suse, arch, ostree, ublue, !zorin
# reboot: yes
# nocontainer
# repo: https://github.com/CachyOS/CachyOS-Settings
# optimized-only: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/optimizers.lib"
_lang_
sudo_rq
if command -v rpm-ostree &>/dev/null; then
    if [ "$ID" = "bluefin" ] || [ "$ID" = "bazzite" ] || [ "$ID" = "aurora" ]; then
        cfg_host=$(rpm -qi "optimize-cfg-ublue" 2>/dev/null | grep "^Version" | awk '{print $3}')
        cfg_server="1.0"
    else
        cfg_host=$(rpm -qi "linuxtoys-cfg-atom" 2>/dev/null | grep "^Version" | awk '{print $3}')
        cfg_server="1.1"
    fi
    if [ "$cfg_host" != "$cfg_server" ]; then
        if [ "$ID" = "bluefin" ] || [ "$ID" = "bazzite" ] || [ "$ID" = "aurora" ]; then
            wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/optimize-cfg-ublue/rpmbuild/RPMS/x86_64/optimize-cfg-ublue-1.0-1.x86_64.rpm
            if rpm -qi "optimize-cfg-ublue" &>/dev/null; then
                pkg_remove optimize-cfg-ublue
            fi
            pkg_fromfile optimize-cfg-ublue-1.0-1.x86_64.rpm
        else
            wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/optimize-cfg-ostree/rpmbuild/RPMS/x86_64/linuxtoys-cfg-atom-1.1-1.x86_64.rpm
            if rpm -qi "linuxtoys-cfg-atom" &>/dev/null; then
                pkg_remove linuxtoys-cfg-atom
            fi
            pkg_fromfile linuxtoys-cfg-atom-1.1-1.x86_64.rpm
        fi
    else
        zenity --info --text "$msg281" --height=300 --width=300
    fi
else
    if ! is_solus && [ ! -f /usr/lib/sysctl.d/70-cachyos-settings.conf ]; then
        cachyos_sysd_lib
    elif is_solus && [ ! -f /usr/lib/udev/rules.d/99-cpu-dma-latency.rules ]; then
        cachyos_sysd_lib
    else
        zenity --info --text "$msg281" --height=300 --width=300
    fi
fi
