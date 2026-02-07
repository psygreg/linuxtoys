#!/bin/bash
# name: psycachy
# version: 1.0
# description: psycachy_desc
# icon: psycachy.svg
# compat: ubuntu, debian, !zorin
# reboot: yes
# noconfirm: yes
# nocontainer
# repo: https://codeberg.org/psygreg/linux-psycachy

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
# get current tags and versions
lts_tag="$(curl -s "https://codeberg.org/api/v1/repos/psygreg/linux-psycachy/releases" | grep -o '"tag_name":"[^"]*"' | cut -d'"' -f4 | grep -i '^LTS-' | sort -Vr | head -n 1)"
std_tag="$(curl -s "https://codeberg.org/api/v1/repos/psygreg/linux-psycachy/releases" | grep -o '"tag_name":"[^"]*"' | cut -d'"' -f4 | grep -i '^STD-' | sort -Vr | head -n 1)"
kver_lts="$(echo "$lts_tag" | cut -d'-' -f2-)"
kver_psycachy="$(echo "$std_tag" | cut -d'-' -f2-)"

# get current running kernel version (just the version number)
current_kver="$(uname -r | cut -d'-' -f1)"

# get all Ubuntu tags and find a match with current kernel version
ubuntu_tag=""
kver_ubuntu=""

# fetch all Ubuntu tags and iterate to find a match
while IFS= read -r tag; do
    # skip empty lines
    [ -z "$tag" ] && continue
    
    tag_version="$(echo "$tag" | cut -d'-' -f2-)"
    if [ "$tag_version" = "$current_kver" ]; then
        ubuntu_tag="$tag"
        kver_ubuntu="$tag_version"
        break
    fi
done < <(curl -s "https://codeberg.org/api/v1/repos/psygreg/linux-psycachy/releases" | grep -o '"tag_name":"[^"]*"' | cut -d'"' -f4 | grep -i '^Ubuntu-')
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
    wget "https://codeberg.org/psygreg/linux-psycachy/releases/download/${std_tag}/linux-headers-psycachy_${kver_psycachy}-1_amd64.deb"
    wget "https://codeberg.org/psygreg/linux-psycachy/releases/download/${std_tag}/linux-image-psycachy_${kver_psycachy}-1_amd64.deb"
    wget "https://codeberg.org/psygreg/linux-psycachy/releases/download/${std_tag}/linux-libc-dev_${kver_psycachy}-1_amd64.deb"
    sleep 1
    sudo dpkg -i linux-image-psycachy_${kver_psycachy}-1_amd64.deb linux-headers-psycachy_${kver_psycachy}-1_amd64.deb linux-libc-dev_${kver_psycachy}-1_amd64.deb || exit 10
    sleep 1
    rm linux-image-psycachy_${kver_psycachy}-1_amd64.deb
    rm linux-headers-psycachy_${kver_psycachy}-1_amd64.deb
    rm linux-libc-dev_${kver_psycachy}-1_amd64.deb
    # sign kernel image for secure boot
    if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
        bash <(curl -s https://codeberg.org/psygreg/linux-psycachy/raw/branch/master/secureboot/create-key.sh) --linuxtoys
    fi
}
# psycachy lts edition
psycachy_lts () {
    cd $HOME
    wget "https://codeberg.org/psygreg/linux-psycachy/releases/download/${lts_tag}/linux-headers-psycachy-lts_${kver_lts}-1_amd64.deb"
    wget "https://codeberg.org/psygreg/linux-psycachy/releases/download/${lts_tag}/linux-image-psycachy-lts_${kver_lts}-1_amd64.deb"
    wget "https://codeberg.org/psygreg/linux-psycachy/releases/download/${lts_tag}/linux-libc-dev_${kver_lts}-1_amd64.deb"
    sleep 1
    sudo dpkg -i linux-image-psycachy-lts_${kver_lts}-1_amd64.deb linux-headers-psycachy-lts_${kver_lts}-1_amd64.deb linux-libc-dev_${kver_lts}-1_amd64.deb || exit 10
    sleep 1
    rm linux-image-psycachy-lts_${kver_lts}-1_amd64.deb
    rm linux-headers-psycachy-lts_${kver_lts}-1_amd64.deb
    rm linux-libc-dev_${kver_lts}-1_amd64.deb
    # sign kernel image for secure boot
    if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
        bash <(curl -s https://codeberg.org/psygreg/linux-psycachy/raw/branch/master/secureboot/create-key.sh) --lts
    fi
}
# psycachy for ubuntu lts with dkms support
psycachy_ubuntu () {
    cd $HOME
    wget "https://codeberg.org/psygreg/linux-psycachy/releases/download/${ubuntu_tag}/linux-headers-psycachy-lts_${kver_ubuntu}-1_amd64.deb"
    wget "https://codeberg.org/psygreg/linux-psycachy/releases/download/${ubuntu_tag}/linux-image-psycachy-lts_${kver_ubuntu}-1_amd64.deb"
    wget "https://codeberg.org/psygreg/linux-psycachy/releases/download/${ubuntu_tag}/linux-libc-dev_${kver_ubuntu}-1_amd64.deb"
    sleep 1
    sudo dpkg -i linux-image-psycachy-lts_${kver_ubuntu}-1_amd64.deb linux-headers-psycachy-lts_${kver_ubuntu}-1_amd64.deb linux-libc-dev_${kver_ubuntu}-1_amd64.deb || exit 10
    sleep 1
    rm linux-image-psycachy-lts_${kver_ubuntu}-1_amd64.deb
    rm linux-headers-psycachy-lts_${kver_ubuntu}-1_amd64.deb
    rm linux-libc-dev_${kver_ubuntu}-1_amd64.deb
    # sign kernel image for secure boot
    if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
        bash <(curl -s https://codeberg.org/psygreg/linux-psycachy/raw/tag/Ubuntu-6.14.11/secureboot/create-key.sh) -u
    fi
}
# Parse command line arguments
if [ "$1" = "-s" ] || [ "$1" = "--standard" ]; then
    # Direct installation of standard edition
    psycachy_std && exit 0
elif [ "$1" = "-l" ] || [ "$1" = "--lts" ]; then
    # Direct installation of LTS edition
    psycachy_lts && exit 0
elif [ "$1" = "-u" ] || [ "$1" = "--ubuntu" ]; then
    psycachy_ubuntu && exit 0
else
    # Show menu if no arguments provided
    while true; do
        # Build menu options dynamically
        menu_options=("Standard" "LTS")
        
        # Only add Ubuntu option if a matching version was found
        if [ -n "$kver_ubuntu" ]; then
            menu_options+=("Ubuntu LTS with DKMS support")
        fi
        
        menu_options+=("Cancel")
        
        CHOICE=$(zenity --list --title "Psycachy Kernel Installer" --text "Select the kernel version to install:" \
            --column "Versions" \
            "${menu_options[@]}" \
            --width 360 --height 360)

        if [ $? -ne 0 ]; then
            exit 100
        fi

        case $CHOICE in
        Standard) psycachy_std && exit 0 ;;
        LTS) psycachy_lts && exit 0 ;;
        "Ubuntu LTS 24 with DKMS support") psycachy_ubuntu && exit 0 ;;
        Cancel | q) exit 100 ;;
        *) echo "Invalid Option" ;;
        esac
    done
fi
