#!/bin/bash

# system-agnostic scripts
sysag_run () {

    if [[ "$ID" != "cachyos" ]]; then
        cachyos_sysd_lib
    fi
    sboost_lib
    # set safe minimum ram to use preload
    local total_kb=$(grep MemTotal /proc/meminfo | awk '{ print $2 }')
    local total_gb=$(( total_kb / 1024 / 1024 ))
    _cram=$(( total_gb ))
    if (( _cram < 16 )); then
        preload_lib
    fi
    dsplitm_lib
    flatpak_in_lib
    if command -v flatpak &> /dev/null; then
        if [ "$ID" == "ubuntu" ]; then
            insta gnome-software gnome-software-plugin-flatpak gnome-software-plugin-snap
        fi
    fi

}

# consolidated installation
optimizer () {

    if [ ! -f /.autopatch.state ]; then
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            debfixer_lib
            # summon installer
            if whiptail --title "CachyOS Kernel" --yesno "$msg150" 12 78; then
                psycachy_lib
                kupid_lib
            fi
            # clean old kernels
            dpkg --list | grep -v $(uname -r) | grep -E 'linux-image-[0-9]|linux-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            dpkg --list | grep -v $(uname -r) | grep -E 'custom-kernel-[0-9]|custom-kernel-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            # run system-agnostic optimizations
            sysag_run
            local title="$msg006"
            local msg="$msg036"
            _msgbox_
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            if whiptail --title "CachyOS Kernel" --yesno "$msg150" 12 78; then
                fedora_cachyos_menu_lib
            fi
            # run system-agnostic optimizations
            sysag_run
        elif [[ "$ID" =~ ^(arch)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            if whiptail --title "CachyOS Kernel" --yesno "$msg150" 12 78; then
                cachyos_arch_lib
            fi
            # run system-agnostic optimizations
            sysag_run
            local title="$msg006"
            local msg="$msg036"
            _msgbox_
        elif [ "$ID" == "cachyos" ]; then
            sysag_run
            local title="$msg006"
            local msg="$msg036"
            _msgbox_
        else
            local title="$msg074"
            local msg="$msg077"
            _msgbox_
        fi
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/autopatch.state
        sudo mv autopatch.state /.autopatch.state
    else
        local title="AutoPatcher"
        local msg="$msg234"
        _msgbox_
    fi

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
# language
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
# menu
while :; do

    CHOICE=$(whiptail --title "Power Optimizer" --menu "$msg229" 25 78 16 \
        "0" "Desktop" \
        "1" "Laptop" \
        "2" "Cancel" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) optimizer && break ;;
    1) optimizer && psave_lib && break ;;
    2 | q) break ;;
    *) echo "Invalid Option" ;;
    esac
done
