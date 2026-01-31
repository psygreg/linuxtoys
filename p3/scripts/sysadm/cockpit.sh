#!/bin/bash
# name: Cockpit Server
# version: 1.0
# description: cockpit_desc
# icon: cockpit.png

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
if [ "$ID" == "debian" ]; then
    sudo bash -c 'echo "deb http://deb.debian.org/debian ${VERSION_CODENAME}-backports main" > \
    /etc/apt/sources.list.d/backports.list'
    sudo apt update
    sudo apt install -y -t ${VERSION_CODENAME}-backports cockpit
elif [ "$ID" == "ubuntu" ] || [[ "$ID_LIKE" =~ "ubuntu" ]]; then
    sudo apt install -y -t ${VERSION_CODENAME}-backports cockpit
fi
if command -v rpm-ostree &>/dev/null; then
    _packages=(cockpit-system cockpit-ostree cockpit-podman cockpit-kdump cockpit-networkmanager)
else
    _packages=(cockpit)
fi
_install_
sudo systemctl enable --now cockpit.socket
if [[ "$ID" =~ "fedora" ]] || [[ "$ID" =~ "rhel" ]] || [[ "$ID_LIKE" =~ "fedora" ]]; then
    sudo firewall-cmd --add-service=cockpit
    sudo firewall-cmd --add-service=cockpit --permanent
elif [[ "$ID" =~ "suse" ]]; then
    sudo firewall-cmd --permanent --zone=public --add-service=cockpit
    sudo firewall-cmd --reload
fi
zeninf "$msg018"