#!/bin/bash
source <(curl -s https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/linuxtoys.lib)

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
        # install iwd
        insta iwd
        # enforce iwd backend for networkmanager
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/src/resources/other/iwd.conf
        sudo mv iwd.conf /etc/NetworkManager/conf.d/
        # restart networkmanager with wpasupplicant disabled
        sudo systemctl stop NetworkManager
        sudo systemctl disable --now wpa_supplicant
        sudo systemctl restart NetworkManager
        return 0
    else
        local title="Cancelled"
        local msg="No WiFi device found."
        _msgbox_
        return 2
    fi

}

# disable iwd
iwd_rm () {

    if [ -f "/etc/NetworkManager/conf.d/iwd.conf" ]; then
        sudo rm /etc/NetworkManager/conf.d/iwd.conf
        sudo systemctl stop NetworkManager
        sudo systemctl enable --now wpa_supplicant
        sudo systemctl restart NetworkManager
        return 0
    else
        local title="Cancelled"
        local msg="iwd.conf file not found. IWD was not enabled in this system."
        _msgbox_
        return 1
    fi

}

# menu
while :; do

    CHOICE=$(whiptail --title "iNet Wireless Daemon" --menu "" 25 78 16 \
        "0" "Install" \
        "1" "Remove" \
        "2" "Cancel" 3>&1 1>&2 2>&3)

    exitstatus=$?
    if [ $exitstatus != 0 ]; then
        # Exit the script if the user presses Esc
        break
    fi

    case $CHOICE in
    0) iwd_in && break;;
    1) iwd_rm && break;;
    2 | q) break ;;
    *) echo "Invalid Option" ;;
    esac

done
