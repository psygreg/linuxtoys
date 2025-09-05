#!/usr/bin/env bash
# name: Sublime Text
# version: 4
# description: sublime_desc
# icon: sublime.png

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
# Instalação para Debian e Ubuntu
if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
    wget -qO - https://download.sublimetext.com/sublimehq-pub.gpg | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/sublimehq-archive.gpg > /dev/null
    echo "deb https://download.sublimetext.com/ apt/stable/" | sudo tee /etc/apt/sources.list.d/sublime-text.list
    sudo apt-get update
    _packages=(sublime-text)
    _install_
# Instalação para Fedora e derivados
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
    sudo rpm -v --import https://download.sublimetext.com/sublimehq-rpm-pub.gpg
    if command -v rpm-ostree &>/dev/null; then
        {
            echo "[sublime-text]"
            echo "name=Sublime Text - Stable"
            echo "baseurl=https://download.sublimetext.com/rpm/stable/x86_64"
            echo "enabled=1"
            echo "gpgcheck=1"
            echo "gpgkey=https://download.sublimetext.com/sublimehq-rpm-pub.gpg"
        } | sudo tee /etc/yum.repos.d/sublime-text.repo > /dev/null
        rpm-ostree refresh-md
    else
        sudo dnf config-manager --add-repo https://download.sublimetext.com/rpm/stable/x86_64/sublime-text.repo
    fi
    _packages=(sublime-text)
    _install_
# Instalação para Arch Linux e derivados
elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
    curl -O https://download.sublimetext.com/sublimehq-pub.gpg && sudo pacman-key --add sublimehq-pub.gpg && sudo pacman-key --lsign-key 8A8F901A && rm sublimehq-pub.gpg
    echo -e "\n[sublime-text]\nServer = https://download.sublimetext.com/arch/stable/x86_64" | sudo tee -a /etc/pacman.conf
    sudo pacman -Syu
    _packages=(sublime-text)
    _install_
else
    fatal $"This script is not compatible with your operating system."
fi
zeninf $"Operations completed."