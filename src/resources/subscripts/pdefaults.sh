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
    # add alive timeout fix for Gnome
    if echo "$XDG_CURRENT_DESKTOP" | grep -qi 'gnome'; then
        dconf write /org/gnome/mutter/check-alive-timeout "20000"
    fi

}

# consolidated installation
optimizer () {

    if [ ! -f /.autopatch.state ]; then
        if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
            debfixer_lib
            # summon installer
            if zenity --question --text "$msg150" --width 360 --height 300; then
                psycachy_lib
                kupid_lib
            fi
            # clean old kernels
            dpkg --list | grep -v $(uname -r) | grep -E 'linux-image-[0-9]|linux-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            dpkg --list | grep -v $(uname -r) | grep -E 'custom-kernel-[0-9]|custom-kernel-headers-[0-9]' | awk '{print $2" "$3}' | sort -k2,2 | head -n -2 | awk '{print $1}' | xargs sudo apt purge
            # run system-agnostic optimizations
            sysag_run
            zeninf "$msg036"
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            if zenity --question --text "$msg150" --width 360 --height 300; then
                fedora_cachyos_menu_lib
            fi
            # run system-agnostic optimizations
            sysag_run
        elif [[ "$ID" =~ ^(arch)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
            if zenity --question --text "$msg150" --width 360 --height 300; then
                cachyos_arch_lib
            fi
            # run system-agnostic optimizations
            sysag_run
            zeninf "$msg036"
        elif [ "$ID" == "cachyos" ]; then
            sysag_run
            zeninf "$msg036"
        else
            nonfatal "$msg077"
            exit 1
        fi
        if echo "$XDG_CURRENT_DESKTOP" | grep -qi 'gnome'; then
            dconf write /org/gnome/mutter/check-alive-timeout "20000"
        fi
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/autopatch.state
        sudo mv autopatch.state /.autopatch.state
    else
        nonfatal "$msg234"
    fi

}

# runtime
. /etc/os-release
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)
# language
_lang_
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/lang/${langfile})
# menu
while true; do

    CHOICE=$(zenity --list --title "Power Optimizer" --text "$msg229" \
        --column "Options" \
        "Desktop" \
        "Laptop" \
        "Cancel" \
        --width 300 --height 330 )

    if [ $? -ne 0 ]; then
        exit 0
    fi

    case $CHOICE in
    "Desktop") optimizer && break ;;
    "Laptop") optimizer && psave_lib && break ;;
    "Cancel") break ;;
    *) echo "Invalid Option" ;;
    esac
done
