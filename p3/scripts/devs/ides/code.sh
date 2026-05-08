#!/bin/bash
# name: Visual Studio Code
# version: 1.0
# description: code_desc
# icon: code.svg

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
prep_tmp
if is_solus; then
    pkg_install vscode
    zeninf "msg018"
    exit 0
fi
if is_debian || is_ubuntu; then
    sudo curl -fsSLo /usr/share/keyrings/vscode-keyring.asc https://packages.microsoft.com/keys/microsoft.asc
    echo "deb [signed-by=/usr/share/keyrings/vscode-keyring.asc arch=amd64] https://packages.microsoft.com/repos/vscode stable main" | sudo tee /etc/apt/sources.list.d/vscode.list
    sleep 1
    sudo apt update
elif is_arch || is_cachy; then
    pkg_install visual-studio-code-bin
    zeninf "$msg018"
    exit 0
elif is_fedora; then
    if command -v rpm-ostree &>/dev/null; then
        echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" | sudo tee /etc/yum.repos.d/vscode.repo > /dev/null
    else
        sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
        echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\nautorefresh=1\ntype=rpm-md\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" | sudo tee /etc/yum.repos.d/vscode.repo > /dev/null
        sudo dnf check-update
    fi
elif is_suse; then
    sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
    echo -e "[code]\nname=Visual Studio Code\nbaseurl=https://packages.microsoft.com/yumrepos/vscode\nenabled=1\nautorefresh=1\ntype=rpm-md\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" |sudo tee /etc/zypp/repos.d/vscode.repo > /dev/null
fi
pkg_install code
zeninf "$msg018"