#!/bin/bash
# name: iNet Wireless Daemon
# version: 1.0
# description: iwd_desc
# icon: iwd.svg
# reboot: yes
# noconfirm: yes
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# functions
# enable iwd
iwd_in () {
    # detect wifi adapter
    has_wifi=0
    for iface in /sys/class/net/*; do
        if [ -d "$iface/wireless" ]; then
            has_wifi=1
            break
        fi
    done
    # only install if an adapter is found
    if [ $has_wifi -eq 1 ]; then
        sudo_rq
        # install iwd
        if [ "$ID" == "bazzite" ] || [ "$ID" == "bluefin" ] || [ "$ID" == "aurora" ]; then
            # use their iwd installation script for ublue distros
            ujust iwd
        elif command -v rpm-ostree &>/dev/null; then
            sudo rpm-ostree install iwd
            # enforce iwd backend for networkmanager
            wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/iwd.conf
            sudo mv iwd.conf /etc/NetworkManager/conf.d/
            sudo systemctl disable wpa_supplicant
            return 0
        else
            _packages=(iwd)
            _install_
            # enforce iwd backend for networkmanager
            wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/iwd.conf
            sudo mv iwd.conf /etc/NetworkManager/conf.d/
            # restart networkmanager with wpasupplicant disabled
            sudo systemctl stop NetworkManager
            sudo systemctl disable wpa_supplicant
            sleep 1
            sudo systemctl restart NetworkManager
            return 0
        fi
    else
        nonfatal "No WiFi device found."
        return 2
    fi
}
# disable iwd
iwd_rm () {
    if [ -f "/etc/NetworkManager/conf.d/iwd.conf" ]; then
        sudo_rq
        sudo rm /etc/NetworkManager/conf.d/iwd.conf
        sudo systemctl stop NetworkManager
        sudo systemctl enable --now wpa_supplicant
        sudo systemctl restart NetworkManager
        return 0
    else
        nonfatal "iwd.conf file not found. IWD was not enabled in this system."
        return 1
    fi
}
# menu
while true; do
    CHOICE=$(zenity --list --title "iNet Wireless Daemon" \
        --column="Options" \
        "Install" \
        "Remove" \
        "Cancel" \
        --height=360 --width=300)

    if [ $? -ne 0 ]; then
        exit 100
    fi

    case $CHOICE in
        "Install") iwd_in && break;;
        "Remove") iwd_rm && break;;
        "Cancel") exit 100 ;;
        *) echo "Invalid Option" ;;
    esac
done