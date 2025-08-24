#!/bin/bash
# name: pdefaults
# version: 1.0
# description: pdefaults_desc
# icon: optimizer.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy
# reboot: yes
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../libs/optimizers.lib"
# language
_lang_
source "$SCRIPT_DIR/../libs/lang/${langfile}.lib"
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
    # fix video thumbnails
    _packages=(ffmpegthumbnailer)
    _install_
}
# consolidated installation
optimizer () {
    if [ ! -f $HOME/.local/.autopatch.state ]; then
        cd $HOME
        sudo_rq
        if [ "$ID" == "debian" ]; then
            debfixer_lib
        fi
        # system-agnostic optimizations
        sysag_run
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/autopatch.state
        sudo mv autopatch.state $HOME/.local/.autopatch.state
        zeninf "$msg036"
    else
        fatal "$msg234"
    fi
}
# menu
while true; do
    CHOICE=$(zenity --list --title "Power Optimizer" --text "$msg229" \
        --column "Options" \
        "Desktop" \
        "Laptop" \
        "Cancel" \
        --width 300 --height 330 )

    if [ $? -ne 0 ]; then
        exit 100
    fi

    case $CHOICE in
    "Desktop") optimizer && break ;;
    "Laptop") optimizer && psave_lib && break ;;
    "Cancel") exit 100 ;;
    *) echo "Invalid Option" ;;
    esac
done
