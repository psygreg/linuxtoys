#!/bin/bash
# name: Touchégg
# version: 1.0
# description: touchegg_desc
# icon: touchegg.svg
# compat: ubuntu, debian, fedora, suse

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
# get latest release tag for touchegg
tag=$(curl -s "https://api.github.com/repos/JoseExposito/touchegg/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
if [ "$XDG_SESSION_TYPE" != "wayland" ]; then
    sudo_rq
    if [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "ubuntu" ]; then
        cd $HOME
        sudo add-apt-repository ppa:touchegg/stable
        sudo apt update
        sudo apt install touchegg
    elif [ "$ID" == "debian" ] || [[ "$ID_LIKE" == *debian* ]]; then
        cd $HOME
        wget https://github.com/JoseExposito/touchegg/archive/refs/tags/touchegg_${tag}_amd64.deb
        sudo dpkg -i touchegg_${tag}_amd64.deb
    elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ] || [ "$ID_LIKE" == "suse" ] || [ "$ID" == "suse" ] || [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
        if [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [ "$ID" == "fedora" ]; then
            sudo dnf in -y touchegg
        elif [[ "$ID_LIKE" == *suse* ]] || [ "$ID" == "suse" ]; then
            sudo zypper in -y touchegg
        elif [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]] || [[ "$ID" =~ ^(arch|cachyos)$ ]]; then
            sudo pacman -S --noconfirm touchegg
        fi
        sudo systemctl enable touchegg.service
        sudo systemctl start touchegg
    else
        nonfatal "$msg077"
    fi
else
    fatal "$msg077"
fi