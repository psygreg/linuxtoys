#!/bin/bash
# name: Godot Engine 4 Sharp
# version: 1.0
# description: godotsharp_desc
# icon: godot-sharp
# compat: fedora, ubuntu, debian, ostree, ublue, suse

# --- Start of the script code ---
# when there are updates, make sure to edit the .desktop files in resources/godot as well!
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
cd $HOME
if [[ "$ID_LIKE" =~ (rhel|fedora) || "$ID" =~ (fedora|ubuntu|debian) || "$NAME" == "openSUSE Leap" ]]; then
    # first install
    if [ ! -d "$HOME/.local/godot" ]; then
        wget 'https://objects.githubusercontent.com/github-production-release-asset-2e65be/15634981/8976b3a0-fb60-4d98-bd70-b623b9eaf9d3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=releaseassetproduction%2F20250602%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250602T211639Z&X-Amz-Expires=300&X-Amz-Signature=11f42225a48cf9dea2a262ff4918e8c594b8494bd70ac108cf2e0b014fb8ac46&X-Amz-SignedHeaders=host&response-content-disposition=attachment%3B%20filename%3DGodot_v4.4.1-stable_mono_linux_x86_64.zip&response-content-type=application%2Foctet-stream'
        mkdir -p godot
        unzip -d $HOME/godot Godot_v4.4.1-stable_mono_linux.x86_64.zip
        cp -rf godot "$HOME/.local/"
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godot.png
        cp godot.png "$HOME/.local/godot"
        rm -rf godot
        rm godot.png
        rm Godot_v4.4.1-stable_mono_linux.x86_64.zip
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godotsharp.desktop
        cp godotsharp.desktop "$HOME/.local/share/applications"
        rm godotsharp.desktop
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
    else # update
        wget 'https://objects.githubusercontent.com/github-production-release-asset-2e65be/15634981/8976b3a0-fb60-4d98-bd70-b623b9eaf9d3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=releaseassetproduction%2F20250602%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20250602T211639Z&X-Amz-Expires=300&X-Amz-Signature=11f42225a48cf9dea2a262ff4918e8c594b8494bd70ac108cf2e0b014fb8ac46&X-Amz-SignedHeaders=host&response-content-disposition=attachment%3B%20filename%3DGodot_v4.4.1-stable_mono_linux_x86_64.zip&response-content-type=application%2Foctet-stream'
        mkdir -p godot
        unzip -d $HOME/godot Godot_v4.4.1-stable_mono_linux.x86_64.zip
        rm -rf "$HOME/.local/godot"
        cp -rf godot "$HOME/.local/"
        rm -rf godot
        rm Godot_v4.4.1-stable_mono_linux.x86_64.zip
    fi
    zeninf "$msg018"
else
    fatal "$msg077"
fi