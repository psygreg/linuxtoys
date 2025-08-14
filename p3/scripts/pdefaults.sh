#!/bin/bash
# name: pdefaults
# version: 1.0
# description: pdefaults_desc
# icon: application-x-executable
# compat: ubuntu, debian, fedora, suse, arch, cachy
# reboot: yes

# --- Start of the script code ---
# system-agnostic scripts
sysag_run () {
    if [[ "$ID" != "cachyos" ]]; then
        # systemd patches
        cachyos_sysd_lib
    fi
    # shader booster
    sboost_lib
    # disable split-lock mitigation, which is not a security feature therefore is safe to disable
    dsplitm_lib
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
            # run system-agnostic optimizations
            sysag_run
            zeninf "$msg036"
        elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            # run system-agnostic optimizations
            sysag_run
        elif [[ "$ID" =~ ^(arch)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
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
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../libs/optimizers.lib"
# language
_lang_
source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"
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
