#!/bin/bash
get_cfgs () {   

    local _cachyos_source="https://raw.githubusercontent.com/CachyOS/CachyOS-Settings/master/usr"
    local _bazzite_source="https://raw.githubusercontent.com/ublue-os/bazzite/refs/heads/main/system_files/desktop/kinoite/usr/lib/udev/rules.d"
    mkdir -p sysctl-config
    sleep 1
    cd sysctl-config
    {
        echo "${_cachyos_source}/lib/udev/rules.d/20-audio-pm.rules"
        echo "${_cachyos_source}/lib/udev/rules.d/40-hpet-permissions.rules"
        echo "${_cachyos_source}/lib/udev/rules.d/50-sata.rules"
        echo "${_cachyos_source}/lib/udev/rules.d/60-ioschedulers.rules"
        echo "${_cachyos_source}/lib/udev/rules.d/69-hdparm.rules"
        echo "${_cachyos_source}/lib/udev/rules.d/99-cpu-dma-latency.rules"
        echo "${_bazzite_source}/80-gpu-reset.rules"
        } > "udev.txt"
    {
        echo "${_cachyos_source}/lib/tmpfiles.d/thp-shrinker.conf"
        echo "${_cachyos_source}/lib/tmpfiles.d/thp.conf"
        } > "tmpfiles.txt"
    {
        echo "${_cachyos_source}/lib/modprobe.d/20-audio-pm.conf"
        echo "${_cachyos_source}/lib/modprobe.d/amdgpu.conf"
        echo "${_cachyos_source}/lib/modprobe.d/blacklist.conf"
        echo "${_cachyos_source}/lib/modprobe.d/nvidia.conf"
        } > "modprobe.txt"
    {
        echo "${_cachyos_source}/lib/sysctl.d/99-cachyos-settings.conf"
        echo "${_cachyos_source}/lib/systemd/journald.conf.d/00-journal-size.conf"
        } > "other.txt"
    sleep 1
    while read -r url; do wget -P udev "$url"; done < udev.txt
    while read -r url; do wget -P tmpfiles "$url"; done < tmpfiles.txt
    while read -r url; do wget -P modprobe "$url"; done < modprobe.txt
    while read -r url; do wget "$url"; done < other.txt
    
}
get_cfgs
exit 0
