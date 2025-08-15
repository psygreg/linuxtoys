#!/bin/bash
# name: Solaar
# version: 1.0
# description: slar_desc
# icon: solaar

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
sudo_rq
if [ "$ID" == "ubuntu" ]; then
    sudo add-apt-repository ppa:solaar-unifying/stable
    sudo apt update
fi
_packages=(solaar)
_install_