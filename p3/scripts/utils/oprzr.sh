#!/bin/bash
# name: OpenRazer
# version: 1.0
# description: oprzr_desc
# icon: gaming.svg

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_packages=(openrazer-meta)
sudo_rq
if [ "$ID" == "ubuntu" ] || [[ "$ID_LIKE" =~ "ubuntu" ]]; then
    sudo add-apt-repository ppa:openrazer/stable
    sudo apt update
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
    _packages+=(kernel-devel)
    _install_
    if command -v rpm-ostree &>/dev/null; then
        cd $HOME
        wget https://openrazer.github.io/hardware:razer.repo
        sudo install -o 0 -g 0 -m644 hardware:razer.repo /etc/yum.repos.d/hardware:razer.repo
        rm razer.repo
    else
        sudo dnf config-manager addrepo --from-repofile=https://openrazer.github.io/hardware:razer.repo
    fi
elif [[ "$ID_LIKE" == *suse* ]]; then
    if grep -qi "slowroll" /etc/os-release; then
        sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Slowroll/hardware:razer.repo
    elif grep -qi "tumbleweed" /etc/os-release; then
        sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Tumbleweed/hardware:razer.repo
    fi
    sudo zypper refresh
fi
_install_