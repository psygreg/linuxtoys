#!/bin/bash
# name: RStudio
# version: 1.0
# description: rstudio_desc
# icon: rstudio.svg
# repo: https://posit.co/products/open-source/rstudio/
# compat: debian, ubuntu, fedora

source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
_api_stable="https://www.rstudio.com/wp-content/downloads.json"

_req=$(curl -fsSL "${_api_stable}" | \
    grep -oP '"url": "\K.*download1.*rstudio-[0-9]{4}[^"]*\.(deb|rpm)(?=")')

readarray -t _pkgs < <(sort -u <<< ${_req})

if is_debian; then
    _pkg_name=$(basename ${_pkgs[0]})
    if curl -fsSL "${_pkgs[0]}" -o "/tmp/${_pkg_name}"; then
        sudo_rq; pkg_install r-base r-base-dev
        if pkg_fromfile "/tmp/${_pkg_name}"; then
            zeninf "RStudio successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        fatal "Failed to download: ${_pkg_name}"
    fi
elif is_fedora; then
    _pkg_name=$(basename ${_pkgs[1]})
    if curl -fsSL "${_pkgs[1]}" -o "/tmp/${_pkg_name}"; then
        sudo_rq; pkg_install R-core R-core-devel
        if pkg_fromfile "/tmp/${_pkg_name}"; then
            zeninf "RStudio successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        fatal "Failed to download: ${_pkg_name}"
    fi
fi