#!/bin/bash
# name: OpenRazer
# version: 1.0
# description: oprzr_desc
# icon: gaming.svg
# compat: ubuntu, debian, fedora, suse, arch, cachy, ostree
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_packages=(openrazer-meta)
sudo_rq
if [ "$ID" == "ubuntu" ] || [[ "$ID_LIKE" =~ "ubuntu" ]]; then
    sudo add-apt-repository ppa:openrazer/stable
    sudo apt update
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
    if command -v rpm-ostree &>/dev/null; then
        cd $HOME
        if ! grep -q "plugdev" /etc/group; then
            sudo bash -c 'grep "plugdev" /lib/group >> /etc/group'
        fi
        sudo usermod -aG plugdev $USER
        # Add ublue-os/akmods COPR repository for openrazer-kmod (needed for rpm-ostree systems)
        wget "https://copr.fedorainfracloud.org/coprs/ublue-os/akmods/repo/fedora-$(rpm -E %fedora)/ublue-os-akmods-fedora-$(rpm -E %fedora).repo"
        sudo install -o 0 -g 0 "ublue-os-akmods-fedora-$(rpm -E %fedora).repo" "/etc/yum.repos.d/ublue-os-akmods-fedora-$(rpm -E %fedora).repo"
        rm "ublue-os-akmods-fedora-$(rpm -E %fedora).repo"
        # Add OpenRazer repository
        wget https://openrazer.github.io/hardware:razer.repo
        sudo install -o 0 -g 0 -m644 hardware:razer.repo /etc/yum.repos.d/hardware:razer.repo
        rm "hardware:razer.repo"
        # Refresh metadata
        rpm-ostree refresh-md
        # Install kmod-openrazer for rpm-ostree systems
        sudo rpm-ostree install kmod-openrazer openrazer-daemon
    else
        _packages+=(kernel-devel)
        # Regular Fedora systems - use standard approach
        sudo dnf config-manager addrepo --from-repofile=https://openrazer.github.io/hardware:razer.repo
        _install_
    fi
elif [[ "$ID_LIKE" == *suse* ]]; then
    if grep -qi "slowroll" /etc/os-release; then
        sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Slowroll/hardware:razer.repo
    elif grep -qi "tumbleweed" /etc/os-release; then
        sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Tumbleweed/hardware:razer.repo
    fi
    sudo zypper refresh
    _install_
fi
flatpak_in_lib
flatpak install -y --system --noninteractive flathub app.polychromatic.controller
zeninf "$msg036"