#!/bin/bash
# name: psycachy
# version: 1.0
# description: psycachy_desc
# icon: psycachy.svg
# compat: ubuntu
# reboot: yes
# noconfirm: yes
# nocontainer
# repo: https://git.linux.toys/psygreg/linux-psycachy

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

# get current running kernel version (just the version number)
current_kver="$(uname -r | cut -d'-' -f1)"
# get all tags and find a match with current kernel version
ubuntu_tag=""
kver_ubuntu=""
# fetch all tags and iterate to find a match
while IFS= read -r tag; do
    # skip empty lines
    [ -z "$tag" ] && continue

    if [ "$tag" = "$current_kver" ]; then
        ubuntu_tag="$tag"
        kver_ubuntu="$tag"
        break
    fi
done < <(curl -s "https://api.github.com/repos/psygreg/linux-psycachy/releases" | grep -o '"tag_name": "[^"]*"' | cut -d'"' -f4)

# early sudo request - fixes error obtaining sudo
sudo_rq
# psycachy for ubuntu lts with dkms support
psycachy_ubuntu () {
    cd $HOME
    wget "https://github.com/psygreg/linux-psycachy/releases/download/${ubuntu_tag}/linux-headers-psycachy_${kver_ubuntu}-3_amd64.deb"
    wget "https://github.com/psygreg/linux-psycachy/releases/download/${ubuntu_tag}/linux-image-psycachy_${kver_ubuntu}-3_amd64.deb"
    wget "https://github.com/psygreg/linux-psycachy/releases/download/${ubuntu_tag}/linux-libc-dev_${kver_ubuntu}-3_amd64.deb"

    sleep 1
    sudo dpkg -i linux-image-psycachy_${kver_ubuntu}-3_amd64.deb linux-headers-psycachy_${kver_ubuntu}-3_amd64.deb linux-libc-dev_${kver_ubuntu}-3_amd64.deb || exit 10
    sleep 1
    rm linux-image-psycachy_${kver_ubuntu}-3_amd64.deb
    rm linux-headers-psycachy_${kver_ubuntu}-3_amd64.deb
    rm linux-libc-dev_${kver_ubuntu}-3_amd64.deb

    # sign kernel image for secure boot
    if sudo mokutil --sb-state | grep -qi "secureboot enabled"; then
        bash <(curl -s https://github.com/psygreg/linux-psycachy/releases/download/${ubuntu_tag}/create-key.sh) -o /tmp/create-key.sh && chmod +x /tmp/create-key.sh && /tmp/create-key.sh -u
    fi
    zeninf "Tasks completed. Remember to reinstall any DKMS modules (e.g. NVIDIA) before rebooting to use the new kernel."
}
# for updates, ignore version check since the currently running kernel will be an older psycachy
if [ "$1" = "-u" ] || [ "$1" = "--ubuntu" ]; then
    ubuntu_tag=$(curl -s "https://api.github.com/repos/psygreg/linux-psycachy/releases/latest" | grep -o '"tag_name": "[^"]*"' | cut -d'"' -f4)
    kver_ubuntu="$ubuntu_tag"
    psycachy_ubuntu
    exit 0
else
    # Show menu if no arguments provided
    while true; do
        # Build menu options dynamically
        menu_options=("")

        # Only add Ubuntu option if a matching version was found
        if [ -n "$kver_ubuntu" ]; then
            menu_options+=("Ubuntu LTS with DKMS support")
        else
            menu_options+=("Not available for your OS")
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
        "Not available for your OS") exit 100 ;;
        "Ubuntu with DKMS support") psycachy_ubuntu && exit 0 ;;
        Cancel | q) exit 100 ;;
        *) echo "Invalid Option" ;;
        esac
    done
fi
