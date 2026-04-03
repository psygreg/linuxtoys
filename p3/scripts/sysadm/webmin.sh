#!/bin/bash
# name: Webmin
# version: 1.1
# description: webmin_desc
# icon: webmin.png
# compat: debian, ubuntu, fedora

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq

# Ensure curl is available before downloading repo setup script.
if ! command -v curl >/dev/null 2>&1; then
    if is_debian; then
        sudo apt update || fatal "Failed to update apt package index."
    fi
    _packages=(curl)
    _install_
    command -v curl >/dev/null 2>&1 || fatal "curl command not found after installation attempt."
fi

if ! curl -fsSL -o /tmp/webmin-setup-repo.sh https://raw.githubusercontent.com/webmin/webmin/master/webmin-setup-repo.sh; then
    fatal "Failed to download Webmin repository setup script."
fi

if ! sudo sh /tmp/webmin-setup-repo.sh -f; then
    rm -f /tmp/webmin-setup-repo.sh
    fatal "Failed to setup Webmin repository."
fi

rm -f /tmp/webmin-setup-repo.sh
_packages=(webmin)
_install_
zeninf "$msg018"

