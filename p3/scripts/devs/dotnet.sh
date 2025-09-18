#!/bin/bash
# name: .NET SDK
# version: 1.0
# description: dotnet_desc
# icon: dotnet.svg
# compat: fedora, suse, ostree, debian, ubuntu, ublue

# --- Start of the script code ---
# I am aware there is an AUR package for this. But AUR packages cannot be presumed safe, and it is not officially supported by Microsoft.
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
cd $HOME
sudo_rq
if [ "$ID" == "debian" ]; then
    wget https://packages.microsoft.com/config/debian/12/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
    sudo dpkg -i packages-microsoft-prod.deb
    rm packages-microsoft-prod.deb
    sudo apt update
elif [[ "$NAME" =~ "openSUSE Leap" ]]; then
    sudo zypper in libicu -y
    sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
    wget https://packages.microsoft.com/config/opensuse/15/prod.repo
    sudo mv prod.repo /etc/zypp/repos.d/microsoft-prod.repo
    sudo chown root:root /etc/zypp/repos.d/microsoft-prod.repo
fi
_packages=(dotnet-sdk-9.0)
_install_
zeninf "$msg018"