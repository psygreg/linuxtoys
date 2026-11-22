#!/bin/bash
# name: Positron
# version: 1.0
# description: positron_desc
# icon: positron.png
# repo: https://positron.posit.co/
# compat: debian, ubuntu, fedora, rhel

source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
_tag=$(curl -s "https://api.github.com/repos/posit-dev/positron/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
[ -z ${_tag} ] && { fatal "It was not possible to obtain the latest available version of positron."; exit 1;}

if is_debian || is_ubuntu; then
	_link="https://cdn.posit.co/positron/releases/deb/x86_64/Positron-${_tag}-x64.deb"
    _pkg_name=$(basename ${_link})
    if curl -fsSL "${_link}" -o "/tmp/${_pkg_name}"; then
        # The deb bundles VS Code extension VSIXs (e.g. ms-toolsai.jupyter)
        # that ship multi-platform .node prebuilds (win32/darwin/linux) as
        # inert data; --guest declares them while native amd64 metadata and
        # host-ISA payload evidence stay mandatory.
        _architecture_check files --content-kind guest "/tmp/${_pkg_name}"
        pkg_install r-base r-base-dev
        if pkg_fromfile --guest "/tmp/${_pkg_name}"; then
            zeninf "Positron successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        fatal "Failed to download: ${_pkg_name}"
    fi
elif is_fedora || is_rhel; then
	_link="https://cdn.posit.co/positron/releases/rpm/x86_64/Positron-${_tag}-x64.rpm"
    _pkg_name=$(basename ${_link})
    if curl -fsSL "${_link}" -o "/tmp/${_pkg_name}"; then
        # Same multi-platform .node prebuilds inside the bundled extension
        # VSIXs; --guest declares them as inert data (see the deb branch).
        _architecture_check files --content-kind guest "/tmp/${_pkg_name}"
        pkg_install R-core R-core-devel
        if pkg_fromfile --guest "/tmp/${_pkg_name}"; then
            zeninf "Positron successfully installed!"
        else
            fatal "Installation failed."
        fi
    else
        fatal "Failed to download: ${_pkg_name}"
    fi
fi