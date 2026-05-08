#!/bin/bash
# name: OpenRazer
# version: 1.0
# description: oprzr_desc
# icon: gaming.svg
# compat: !ublue
# nocontainer
# repo: https://openrazer.github.io

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_ubuntu; then
    sudo add-apt-repository ppa:openrazer/stable
    sudo apt update
elif is_ostree; then
    prep_tmp
    if ! grep -q "plugdev" /etc/group; then
        sudo bash -c 'grep "plugdev" /lib/group >> /etc/group'
    fi
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
    pkg_install kmod-openrazer openrazer-daemon
elif is_fedora; then
    pkg_install kernel-devel
    # Regular Fedora systems - use standard approach
    sudo dnf config-manager addrepo --from-repofile=https://openrazer.github.io/hardware:razer.repo
elif is_suse; then
    if grep -qi "slowroll" /etc/os-release; then
        sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Slowroll/hardware:razer.repo
    elif grep -qi "tumbleweed" /etc/os-release; then
        sudo zypper addrepo https://download.opensuse.org/repositories/hardware:razer/openSUSE_Tumbleweed/hardware:razer.repo
    fi
    sudo zypper refresh
fi
if is_solus; then
    pkg_install openrazer openrazer-current
else
    pkg_install openrazer-meta
fi
if is_arch || is_cachy; then
    sudo gpasswd -a $USER openrazer
else    
    sudo gpasswd -a $USER plugdev
fi
pkg_flat app.polychromatic.controller
zeninf "$msg036"