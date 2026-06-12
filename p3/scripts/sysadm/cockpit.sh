#!/bin/bash
# name: Cockpit Server
# version: 1.0
# description: cockpit_desc
# icon: cockpit.png
# systemd: yes

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_debian; then
    prep_create /etc/apt/sources.list.d/backports.list
    sudo bash -c 'echo "deb http://deb.debian.org/debian ${VERSION_CODENAME:-trixie}-backports main" > \
    /etc/apt/sources.list.d/backports.list'
    sudo apt update
    sudo apt install -t ${VERSION_CODENAME:-trixie}-backports cockpit || fatal "Failed to install Cockpit from debian backports repository"
    _append_transmap "pkg cockpit"
elif is_ostree; then
    pkg_install --ostreecheck cockpit-system cockpit-ostree cockpit-podman cockpit-kdump cockpit-networkmanager
else
    pkg_install cockpit
fi
sysd_enable cockpit.socket
sysd_start cockpit.socket
if is_fedora || is_ostree; then
    sudo firewall-cmd --add-service=cockpit
    sudo firewall-cmd --add-service=cockpit --permanent
elif is_suse; then
    sudo firewall-cmd --permanent --zone=public --add-service=cockpit
    sudo firewall-cmd --reload
fi
zeninf "$msg018"