#!/bin/bash
# NAME: AnyDesk
# VERSION: 1.0
# DESCRIPTION: anydesk_desc
# icon: anydesk.svg
# repo: https://www.anydesk.com
# compat: fedora, ostree, rhel, debian, ubuntu, suse

# --- Start of the script code ---
prep_tmp_noram
askpass

if is_ubuntu || is_debian; then
    sudo apt install ca-certificates curl apt-transport-https # uninstalling those can cause problems, so better left unregistered
    sudo install -m 0755 -d /etc/apt/keyrings
    prep_create /etc/apt/keyrings/keys.anydesk.com.asc
    sudo curl -fsSL https://keys.anydesk.com/repos/DEB-GPG-KEY -o /etc/apt/keyrings/keys.anydesk.com.asc
    sudo chmod a+r /etc/apt/keyrings/keys.anydesk.com.asc

    prep_create /etc/apt/sources.list.d/anydesk-stable.list
    echo "deb [signed-by=/etc/apt/keyrings/keys.anydesk.com.asc] https://deb.anydesk.com all main" | sudo tee /etc/apt/sources.list.d/anydesk-stable.list > /dev/null
    sudo apt update
else
    prep_create /etc/yum.repos.d/AnyDesk-RPM.repo
    sudo tee /etc/yum.repos.d/AnyDesk-RPM.repo > /dev/null << "EOF"
[anydesk]
name=AnyDesk - stable
baseurl=http://rpm.anydesk.com/$basearch/
gpgcheck=1
repo_gpgcheck=1
gpgkey=https://keys.anydesk.com/repos/RPM-GPG-KEY
EOF
fi

pkg_install anydesk

info "$finishmsg"
