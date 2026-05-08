#!/bin/bash
# name: iNet Wireless Daemon
# version: 1.0
# description: iwd_desc
# icon: iwd.svg
# reboot: yes
# noconfirm: yes
# compat
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
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
        prep_tmp
        sudo_rq
        # install iwd
        if [ "$ID" == "bazzite" ] || [ "$ID" == "bluefin" ] || [ "$ID" == "aurora" ]; then
            # use their iwd installation script for ublue distros
            ujust iwd
            return 0
        elif command -v rpm-ostree &>/dev/null; then
            pkg_install iwd
            # enforce iwd backend for networkmanager
            prep_create /etc/NetworkManager/conf.d/iwd.conf
            wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/iwd.conf
            move_ iwd.conf /etc/NetworkManager/conf.d/
            sysd_disable wpa_supplicant
            sysd_enable iwd
            return 0
        else
            pkg_install iwd
            if is_solus; then
                pkg_install network-manager-iwd
            fi
            # enforce iwd backend for networkmanager
            if is_solus; then
                sysd_disable wpa_supplicant
                sysd_stop wpa_supplicant
                sysd_enable iwd
                sysd_start iwd
            else
                prep_create /etc/NetworkManager/conf.d/iwd.conf
                wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/master/resources/iwd.conf
                move_ iwd.conf /etc/NetworkManager/conf.d/
                # restart networkmanager with wpasupplicant disabled
                sysd_disable wpa_supplicant
                sysd_enable iwd
                sysd_stop wpa_supplicant
                sysd_start iwd
            fi
            return 0
        fi
    else
        nonfatal "No WiFi device found."
        return 2
    fi
}
iwd_in