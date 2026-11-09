#!/bin/bash
# name: RStudio
# version: 1.0
# description: rstudio_desc
# icon: rstudio.svg
# repo: https://posit.co/products/open-source/rstudio/
# compat: debian, ubuntu, fedora, rhel

# reinstate it when API gets back online: debian, ubuntu, fedora, rhel
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
_api_stable="https://cdn.posit.co/downloads.json"

_req=$(curl -fsSL "${_api_stable}" | \
    grep -oP '"url": "\K.*download1.*rstudio-[0-9]{4}[^"]*\.(deb|rpm)(?=")')

_release_file=$(mktemp) || fatal "Cannot stage RStudio metadata"
trap 'rm -f "$_release_file"' EXIT
printf '%s\n' "$_req" | python3 -c 'import json,sys; from urllib.parse import urlsplit,unquote; print(json.dumps({"assets":[{"name":unquote(urlsplit(u).path.rsplit("/",1)[-1]),"browser_download_url":u} for u in sys.stdin.read().splitlines() if u]}))' > "$_release_file"
if is_debian || is_ubuntu; then _package_kind=deb; else _package_kind=rpm; fi
_selected=$(python3 "$SCRIPT_DIR/app/architecture_cli.py" release --kind "$_package_kind" "$_release_file") || fatal "No unique native RStudio package"


if is_debian || is_ubuntu; then
    _pkg_name=$(basename ${_selected})
    if curl -fsSL "${_selected}" -o "/tmp/${_pkg_name}"; then
        _architecture_check files "/tmp/${_pkg_name}"
        pkg_install r-base r-base-dev
        if pkg_fromfile "/tmp/${_pkg_name}"; then
            zeninf "RStudio successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        fatal "Failed to download: ${_pkg_name}"
    fi
elif is_fedora || is_rhel; then
    _pkg_name=$(basename ${_selected})
    if curl -fsSL "${_selected}" -o "/tmp/${_pkg_name}"; then
        _architecture_check files "/tmp/${_pkg_name}"
        pkg_install R-core R-core-devel
        if pkg_fromfile "/tmp/${_pkg_name}"; then
            zeninf "RStudio successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        fatal "Failed to download: ${_pkg_name}"
    fi
fi
