#!/bin/bash
# name: Adoptium Temurin® JDK
# version: 1.0
# description: adoptium_desc
# icon: adoptium.png
# repo: https://adoptium.net/
# compat: debian, ubuntu, fedora, suse, rhel

source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
askpass
if is_debian || is_ubuntu; then
    pkg_install apt-transport-https gpg
    wget -qO - https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/adoptium.gpg > /dev/null
    if is_debian; then
        _codename=$VERSION_CODENAME
        if [[ "$_codename" != @(trixie|bookworm) ]]; then
            _codename="trixie"
        fi
    else
        _codename=$UBUNTU_CODENAME
    fi
    echo "deb https://packages.adoptium.net/artifactory/deb ${_codename} main" | sudo tee /etc/apt/sources.list.d/adoptium.list
    sudo apt update
elif is_fedora || is_rhel; then
    if is_rhel && [[ "$ID" != "rhel" ]]; then
        DISTRIBUTION_NAME="rhel"
    fi
    sudo tee /etc/yum.repos.d/adoptium.repo > /dev/null <<EOF
[Adoptium]
name=Adoptium
baseurl=https://packages.adoptium.net/artifactory/rpm/${DISTRIBUTION_NAME:-$(. /etc/os-release; echo $ID)}/\$releasever/\$basearch
enabled=1
gpgcheck=1
gpgkey=https://packages.adoptium.net/artifactory/api/gpg/key/public
EOF
elif is_suse;then
    if [[ "$ID" =~ (tumbleweed) ]];then
        die "OpenSUSE Tumbleweed without support"
    fi
    sudo zypper ar -f https://packages.adoptium.net/artifactory/rpm/opensuse/$(. /etc/os-release; echo $VERSION_ID)/$(uname -m) adoptium
else
    die "Unsupported distribution"
fi

pkg_install temurin-25-jdk
info "$finishmsg"