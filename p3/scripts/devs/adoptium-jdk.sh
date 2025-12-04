#!/bin/bash
# name: Adoptium Temurin® JDK
# version: 1.0
# description: adoptium_desc
# icon: adoptium.png
# repo: https://adoptium.net/
# compat: debian, ubuntu, fedora, suse

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"

sudo_rq

if is_debian;then
    _packages=(apt-transport-https gpg)
    _install_
    # Eclipse Adoptium GPG key
    curl -fsSL https://packages.adoptium.net/artifactory/api/gpg/key/public | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/adoptium.gpg > /dev/null
    # Adoptium apt repository
    _codename=$(awk -F= '(/^VERSION_CODENAME/ || /^UBUNTU_CODENAME/) && !found {print $2; found=1}' /etc/os-release)
    echo "deb https://packages.adoptium.net/artifactory/deb ${_codename} main" | sudo tee /etc/apt/sources.list.d/adoptium.list
    # Update
    sudo apt update
elif is_fedora;then
    # Adoptium dnf repository
    cat <<EOF | sudo tee /etc/yum.repos.d/adoptium.repo
[Adoptium]
name=Adoptium
baseurl=https://packages.adoptium.net/artifactory/rpm/$ID/\$releasever/\$basearch
enabled=1
gpgcheck=1
gpgkey=https://packages.adoptium.net/artifactory/api/gpg/key/public
EOF
elif is_suse;then
    if [[ "$ID" =~ (tumbleweed) ]];then
        fatal "OpenSUSE Tumbleweed without support"
    fi
    # Adoptium zypper repository
    sudo zypper ar -f "https://packages.adoptium.net/artifactory/rpm/opensuse/$VERSION_ID/$(uname -m)" adoptium
else
    fatal "Unsupported distribution"
fi

_packages=(temurin-21-jdk)
_install_

zeninf "Adoptium Temurin® JDK installed successfully!"