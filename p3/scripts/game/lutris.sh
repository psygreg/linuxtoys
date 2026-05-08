#!/bin/bash
# name: Lutris
# version: 1.0
# description: lutris_desc
# icon: lutris.svg
# nocontainer: ubuntu, debian, suse, arch
# repo: https://lutris.net

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
if is_fedora || is_ostree; then
    sudo_rq
    rpmfusion_chk
    pkg_install lutris
else
    # use flatpak for all others, since native install usually only works well on Fedora
    pkg_flat net.lutris.Lutris
fi