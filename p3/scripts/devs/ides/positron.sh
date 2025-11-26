#!/bin/bash
# name: Positron
# version: 1.0
# description: Unifies exploration and production work in one free, AI-assisted environment, empowering the full spectrum of data science in Python and R.
# icon: positron.png
# repo: https://positron.posit.co/
# compat: debian, ubuntu, fedora

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"

_tag=$(curl -s "https://api.github.com/repos/posit-dev/positron/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
[ -z ${_tag} ] && { fatal "It was not possible to obtain the latest available version of positron."; exit 1;}

if is_debian; then
	_link="https://cdn.posit.co/positron/releases/deb/x86_64/Positron-${_tag}-x64.deb"
    _pkg_name=$(basename ${_link})
    if curl -fsSL "${_link}" -o "/tmp/${_pkg_name}"; then
        sudo_rq; _packages=(r-base r-base-dev); _install_
        if sudo apt install -y "/tmp/${_pkg_name}"; then
            zeninf "Positron successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        falal "Failed to download: ${_pkg_name}"
    fi
elif is_fedora; then
	_link="https://cdn.posit.co/positron/releases/rpm/x86_64/Positron-${_tag}-x64.rpm"
    _pkg_name=$(basename ${_link})
    if curl -fsSL "${_link}" -o "/tmp/${_pkg_name}"; then
        sudo_rq; _packages=(R-core R-core-devel); _install_
        if sudo dnf install -y "/tmp/${_pkg_name}"; then
            zeninf "Positron successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        fatal "Failed to download: ${_pkg_name}"
    fi
fi