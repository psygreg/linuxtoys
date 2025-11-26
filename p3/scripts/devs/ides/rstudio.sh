#!/bin/bash
# name: RStudio
# version: 1.0
# description: A set of tools built to help you be more productive with R and Python.
# icon: rstudio.svg
# repo: https://posit.co/products/open-source/rstudio/
# compat: debian, ubuntu, fedora

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"

_api_stable="https://www.rstudio.com/wp-content/downloads.json"

_req=$(curl -fsSL "${_api_stable}" | \
    grep -oP '"url": "\K.*download1.*rstudio-[0-9]{4}[^"]*\.(deb|rpm)(?=")')

readarray -t _pkgs < <(sort -u <<< ${_req})

if is_debian; then
    _pkg_name=$(basename ${_pkgs[0]})
    if curl -fsSL "${_pkgs[0]}" -o "/tmp/${_pkg_name}"; then
        sudo_rq; _packages=(r-base r-base-dev); _install_
        if sudo apt install -y "/tmp/${_pkg_name}"; then
            zeninf "RStudio successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        falal "Failed to download: ${_pkg_name}"
    fi
elif is_fedora; then
    _pkg_name=$(basename ${_pkgs[1]})
    if curl -fsSL "${_pkgs[1]}" -o "/tmp/${_pkg_name}"; then
        sudo_rq; _packages=(R-core R-core-devel); _install_
        if sudo dnf install -y "/tmp/${_pkg_name}"; then
            zeninf "RStudio successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        fatal "Failed to download: ${_pkg_name}"
    fi
fi