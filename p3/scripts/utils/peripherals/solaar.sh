#!/bin/bash
# name: Solaar
# version: 1.0
# description: slar_desc
# icon: solaar.svg
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
if [ "$ID" == "ubuntu" ]; then
    sudo add-apt-repository ppa:solaar-unifying/stable
    sudo apt update
fi
_packages=(solaar)
_install_
zeninf "$msg018"