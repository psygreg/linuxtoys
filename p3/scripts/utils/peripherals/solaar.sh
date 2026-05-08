#!/bin/bash
# name: Solaar
# version: 1.0
# description: slar_desc
# icon: solaar.svg
# nocontainer
# repo: https://github.com/pwr-Solaar/Solaar

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_ubuntu; then
    sudo add-apt-repository ppa:solaar-unifying/stable
    sudo apt update
fi
pkg_install solaar
zeninf "$msg018"