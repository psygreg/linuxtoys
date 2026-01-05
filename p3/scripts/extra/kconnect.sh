#!/bin/bash
# name: KDE Connect / GSConnect Fix
# version: 1.0
# description: kconnect_desc
# icon: kconnect.svg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq

# KDE Connect port range
KDECONNECT_PORT_START=1714
KDECONNECT_PORT_END=1764

detect_firewall() {
    if command -v firewall-cmd &> /dev/null && systemctl is-active --quiet firewalld; then
        echo "firewalld"
    elif command -v ufw &> /dev/null && systemctl is-active --quiet ufw; then
        echo "ufw"
    elif command -v iptables &> /dev/null && [ -f /proc/net/iptables_filter ]; then
        echo "iptables"
    else
        echo "none"
    fi
}
configure_firewalld() {
    echo "Configuring firewalld for KDE Connect..."
    sudo firewall-cmd --permanent --add-port=${KDECONNECT_PORT_START}-${KDECONNECT_PORT_END}/tcp
    sudo firewall-cmd --permanent --add-port=${KDECONNECT_PORT_START}-${KDECONNECT_PORT_END}/udp
    sudo firewall-cmd --reload
    echo "firewalld configuration complete."
}
configure_ufw() {
    echo "Configuring ufw for KDE Connect..."
    sudo ufw allow ${KDECONNECT_PORT_START}:${KDECONNECT_PORT_END}/tcp
    sudo ufw allow ${KDECONNECT_PORT_START}:${KDECONNECT_PORT_END}/udp
    echo "ufw configuration complete."
}
configure_iptables() {
    echo "Configuring iptables for KDE Connect..."
    sudo iptables -I INPUT -p tcp --dport ${KDECONNECT_PORT_START}:${KDECONNECT_PORT_END} -j ACCEPT
    sudo iptables -I INPUT -p udp --dport ${KDECONNECT_PORT_START}:${KDECONNECT_PORT_END} -j ACCEPT
    if command -v iptables-save &> /dev/null; then
        sudo sh -c 'iptables-save > /etc/iptables/rules.v4'
    fi
    echo "iptables configuration complete."
}

FIREWALL=$(detect_firewall)
case "$FIREWALL" in
    firewalld)
        configure_firewalld
        ;;
    ufw)
        configure_ufw
        ;;
    iptables)
        configure_iptables
        ;;
    none)
        echo "No active firewall detected."
        ;;
esac
