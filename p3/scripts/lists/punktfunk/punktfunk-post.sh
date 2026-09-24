#!/usr/bin/env bash

sudo_ usermod -aG input "$USER"
sudo_ usermod -aG punktfunk "$USER"

if command -v ufw &>/dev/null; then
    sudo_ ufw allow punktfunk-native
    sudo_ ufw allow punktfunk-web
elif command -v firewall-cmd &>/dev/null; then
    sudo_ firewall-cmd --permanent --add-service=punktfunk-native --add-service=punktfunk-web
    sudo_ firewall-cmd --reload
fi

is_arch && {
    { [ "$ID" = "omarchy" ] && { pkg_install punktfunk-client && punktfunk-omarchy setup; }; } || sysd_enable_usr punktfunk-scripting.service
}

sudo_ loginctl enable-linger "$USER"
