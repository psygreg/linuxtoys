#!/bin/bash
# name: Touchégg
# version: 1.0
# description: touchegg_desc
# icon: touchegg.svg
# compat: ubuntu, debian, fedora, suse
# nocontainer
# repo: https://github.com/JoseExposito/touchegg

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
# get latest release tag for touchegg
tag=$(curl -s "https://api.github.com/repos/JoseExposito/touchegg/releases/latest" | grep -oP '"tag_name": "\K(.*)(?=")')
if [ "$XDG_SESSION_TYPE" != "wayland" ]; then
    sudo_rq
    prep_tmp
    if is_ubuntu; then
        sudo add-apt-repository ppa:touchegg/stable
        sudo apt update
        pkg_install touchegg
    elif is_debian; then
        wget https://github.com/JoseExposito/touchegg/archive/refs/tags/touchegg_${tag}_amd64.deb
        pkg_fromfile touchegg_${tag}_amd64.deb
    else
        pkg_install touchegg
    fi
    sysd_enable touchegg.service
    sysd_start touchegg.service
else
    fatal "$msg077"
fi
