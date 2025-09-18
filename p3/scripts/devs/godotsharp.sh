#!/bin/bash
# name: Godot Engine 4 Sharp
# version: 1.0
# description: godotsharp_desc
# icon: godotsh.svg
# compat: fedora, ubuntu, debian, ostree, ublue, suse

# --- Start of the script code ---
# when there are updates, make sure to edit the .desktop files in resources/godot as well!
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
cd $HOME
if [[ "$ID_LIKE" =~ (rhel|fedora) || "$ID" =~ (fedora|ubuntu|debian) || "$NAME" == "openSUSE Leap" ]]; then
    get_latest_godot_mono_url() {
        curl -s https://api.github.com/repos/godotengine/godot/releases/latest | \
        grep browser_download_url | grep 'stable_mono_linux_x86_64.zip' | head -n 1 | cut -d '"' -f 4
    }
    GODOT_MONO_URL=$(get_latest_godot_mono_url)
    GODOT_MONO_ZIP="Godot_latest_mono_linux.x86_64.zip"

    # first install
    if [ ! -d "$HOME/.local/godot" ]; then
        wget "$GODOT_MONO_URL" -O "$GODOT_MONO_ZIP"
        mkdir -p godot
        unzip -d $HOME/godot "$GODOT_MONO_ZIP"
        cp -rf godot "$HOME/.local/"
        wget https://raw.githubusercontent.com/psygreg/linuxtoys/refs/heads/main/resources/godot/godot.png
        cp godot.png "$HOME/.local/godot"
        rm -rf godot
        rm godot.png
        rm "$GODOT_MONO_ZIP"
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
        wget "$GODOT_MONO_URL" -O "$GODOT_MONO_ZIP"
        mkdir -p godot
        unzip -d $HOME/godot "$GODOT_MONO_ZIP"
        rm -rf "$HOME/.local/godot"
        cp -rf godot "$HOME/.local/"
        rm -rf godot
        rm "$GODOT_MONO_ZIP"
    fi
    zeninf "$msg018"
else
    fatal "$msg077"
fi