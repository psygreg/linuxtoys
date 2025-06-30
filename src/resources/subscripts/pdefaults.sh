#!/bin/bash

# system-agnostic scripts
sysag_run () {

    cachyos_sysd_lib
    sboost_lib
    # set safe minimum ram to use preload
    local total_kb=$(grep MemTotal /proc/meminfo | awk '{ print $2 }')
    local total_gb=$(( total_kb / 1024 / 1024 ))
    _cram=$(( total_gb ))
    if (( _cram < 16 )); then
        preload_lib
    fi
    dsplitm_lib

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
# language
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
# installation
if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
    # summon installer
    if whiptail --title "CachyOS Kernel" --yesno "$msg150" 12 78; then
        psycachy_lib
    fi
    # clean old kernels
    dpkg --list | grep -v $(uname -r) | grep -E 'linux-image-[0-9]|linux-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
    dpkg --list | grep -v $(uname -r) | grep -E 'custom-kernel-[0-9]|custom-kernel-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
    # run system-agnostic optimizations
    sysag_run
    title="$msg006"
    msg="$msg036"
    _msgbox_
    exit 0
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
    if whiptail --title "CachyOS Kernel" --yesno "$msg150" 12 78; then
        fedora_cachyos_menu_lib
    fi
    # run system-agnostic optimizations
    sysag_run
    exit 0
elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
    if whiptail --title "CachyOS Kernel" --yesno "$msg150" 12 78; then
        cachyos_arch_lib
    fi
    # run system-agnostic optimizations
    sysag_run
    title="$msg006"
    msg="$msg036"
    _msgbox_
    exit 0
else
    title="$msg074"
    msg="$msg077"
    _msgbox_
    exit 1
fi
