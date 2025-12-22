#!/bin/bash
# name: psycachy
# version: 1.0
# description: psycachy_desc
# icon: psycachy.svg
# compat: ubuntu, debian, !zorin
# reboot: yes
# noconfirm: yes
# nocontainer
# repo: https://github.com/psygreg/linux-psycachy

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
# get current tags and versions
lts_tag="$(curl -s "https://api.github.com/repos/psygreg/linux-psycachy/releases" | grep -oP '"tag_name": "\K(.*)(?=")' | grep -i '^LTS-' | sort -Vr | head -n 1)"
std_tag="$(curl -s "https://api.github.com/repos/psygreg/linux-psycachy/releases" | grep -oP '"tag_name": "\K(.*)(?=")' | grep -i '^STD-' | sort -Vr | head -n 1)"
kver_lts="$(echo "$lts_tag" | cut -d'-' -f2-)"
kver_psycachy="$(echo "$std_tag" | cut -d'-' -f2-)"
_kv_url_latest=$(curl -s https://www.kernel.org | grep -A 1 'id="latest_link"' | awk 'NR==2' | grep -oP 'href="\K[^"]+')
# extract only the version number
_kv_latest=$(echo $_kv_url_latest | grep -oP 'linux-\K[^"]+')
# remove the .tar.xz extension
_kv_latest=$(basename $_kv_latest .tar.xz)
# early sudo request - fixes error obtaining sudo
sudo_rq
# psycachy standard edition
psycachy_std () {
    cd $HOME
    wget "https://github.com/psygreg/linux-psycachy/releases/download/${std_tag}/linux-headers-psycachy_${kver_psycachy}-1_amd64.deb"
    wget "https://github.com/psygreg/linux-psycachy/releases/download/${std_tag}/linux-image-psycachy_${kver_psycachy}-1_amd64.deb"
    wget "https://github.com/psygreg/linux-psycachy/releases/download/${std_tag}/linux-libc-dev_${kver_psycachy}-1_amd64.deb"
    sleep 1
    sudo dpkg -i linux-image-psycachy_${kver_psycachy}-1_amd64.deb linux-headers-psycachy_${kver_psycachy}-1_amd64.deb linux-libc-dev_${kver_psycachy}-1_amd64.deb || exit 10
    sleep 1
    rm linux-image-psycachy_${kver_psycachy}-1_amd64.deb
    rm linux-headers-psycachy_${kver_psycachy}-1_amd64.deb
    rm linux-libc-dev_${kver_psycachy}-1_amd64.deb
    # sign kernel image for secure boot
    if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
        bash <(curl -s https://raw.githubusercontent.com/psygreg/linux-psycachy/refs/heads/master/secureboot/create-key.sh) --linuxtoys
    fi
}
# psycachy lts edition
psycachy_lts () {
    cd $HOME
    wget "https://github.com/psygreg/linux-psycachy/releases/download/${lts_tag}/linux-headers-psycachy-lts_${kver_lts}-1_amd64.deb"
    wget "https://github.com/psygreg/linux-psycachy/releases/download/${lts_tag}/linux-image-psycachy-lts_${kver_lts}-1_amd64.deb"
    wget "https://github.com/psygreg/linux-psycachy/releases/download/${lts_tag}/linux-libc-dev_${kver_lts}-1_amd64.deb"
    sleep 1
    sudo dpkg -i linux-image-psycachy-lts_${kver_lts}-1_amd64.deb linux-headers-psycachy-lts_${kver_lts}-1_amd64.deb linux-libc-dev_${kver_lts}-1_amd64.deb || exit 10
    sleep 1
    rm linux-image-psycachy-lts_${kver_lts}-1_amd64.deb
    rm linux-headers-psycachy-lts_${kver_lts}-1_amd64.deb
    rm linux-libc-dev_${kver_lts}-1_amd64.deb
    # sign kernel image for secure boot
    if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
        bash <(curl -s https://raw.githubusercontent.com/psygreg/linux-psycachy/refs/heads/master/secureboot/create-key.sh) --lts
    fi
}
# Parse command line arguments
if [ "$1" = "-s" ] || [ "$1" = "--standard" ]; then
    # Direct installation of standard edition
    psycachy_std && exit 0
elif [ "$1" = "-l" ] || [ "$1" = "--lts" ]; then
    # Direct installation of LTS edition
    psycachy_lts && exit 0
else
    # Show menu if no arguments provided
    while true; do
        CHOICE=$(zenity --list --title "Psycachy Kernel Installer" --text "Select the kernel version to install:" \
            --column "Versions" \
            "Standard" \
            "LTS" \
            "Cancel" \
            --width 300 --height 330 )

        if [ $? -ne 0 ]; then
            exit 100
        fi

        case $CHOICE in
        Standard) psycachy_std && exit 0 ;;
        LTS) psycachy_lts && exit 0 ;;
        Cancel | q) exit 100 ;;
        *) echo "Invalid Option" ;;
        esac
    done
fi
