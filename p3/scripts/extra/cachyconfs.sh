#!/bin/bash
# name: cachyconfs
# version: 1.0
# description: cachyconfs_desc
# icon: cachyos.svg
# compat: ubuntu, debian, fedora, suse, arch, !zorin, rhel, !deepin
# reboot: yes
# nocontainer
# repo: https://github.com/CachyOS/CachyOS-Settings
# optimized-only: yes
# systemd: yes

# --- Start of the script code ---
askpass

if ! [ ! -f /usr/lib/sysctl.d/70-linuxtoys-settings.conf ]; then
    prep_tmp
    _cfgsource="https://raw.githubusercontent.com/CachyOS/CachyOS-Settings/master/usr"
    {
        echo "${_cfgsource}/lib/udev/rules.d/20-audio-pm.rules"
        echo "${_cfgsource}/lib/udev/rules.d/60-ioschedulers.rules"
        echo "${_cfgsource}/lib/udev/rules.d/99-cpu-dma-latency.rules"
        } > "udev.txt"
    {
        echo "${_cfgsource}/lib/tmpfiles.d/coredump.conf"
        echo "${_cfgsource}/lib/tmpfiles.d/thp-shrinker.conf"
        echo "${_cfgsource}/lib/tmpfiles.d/thp.conf"
        } > "tmpfiles.txt"
    {
        echo "${_cfgsource}/lib/modprobe.d/amdgpu.conf"
        echo "${_cfgsource}/lib/modprobe.d/blacklist.conf"
        } > "modprobe.txt"
    if [ -z "$laptop_mode" ]; then
        echo "${_cfgsource}/lib/modprobe.d/nvidia.conf" >> "modprobe.txt"
    fi
    {
        echo "https://raw.githubusercontent.com/psygreg/linuxtoys/master/resources/70-linuxtoys-settings.conf"
        echo "${_cfgsource}/lib/systemd/journald.conf.d/00-journal-size.conf"
        echo "${_cfgsource}/share/X11/xorg.conf.d/20-touchpad.conf"
        } > "other.txt"
    prep_dir modprobe.d udev/rules.d tmpfiles.d
    while read -r url; do wget -P modprobe.d "$url"; done < modprobe.txt
    while read -r url; do wget -P udev/rules.d "$url"; done < udev.txt
    while read -r url; do wget -P tmpfiles.d "$url"; done < tmpfiles.txt
    while read -r url; do wget "$url"; done < other.txt
    for file in modprobe.d/* udev/rules.d/* tmpfiles.d/*; do
        prep_create "/usr/lib/$file"
        copy_ -f "$file" "/usr/lib/$file"
    done
    [ -d "/usr/share/X11/xorg.conf.d" ] || prep_dir /usr/share/X11/xorg.conf.d
    prep_create /usr/lib/sysctl.d/70-linuxtoys-settings.conf && copy_ -f 70-linuxtoys-settings.conf /usr/lib/sysctl.d/
    prep_create /usr/lib/systemd/journald.conf.d/00-journal-size.conf && copy_ -f 00-journal-size.conf /usr/lib/systemd/journald.conf.d/
    prep_create /usr/share/X11/xorg.conf.d/20-touchpad.conf && copy_ -f 20-touchpad.conf /usr/share/X11/xorg.conf.d/
else
    info "$notdomsg"
fi

info "$rebootmsg"