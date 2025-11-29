#!/bin/bash
# name: modsign
# version: 1.0
# description: modsign_desc
# icon: sign.svg
# compat: ostree
# reboot: yes
# nocontainer

# --- Start of the script code ---
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
# language
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
if sudo mokutil --sb-state | grep -q "SecureBoot enabled"; then
    if ! rpm -qi "akmods-keys" &>/dev/null; then
        _packages=(rpmdevtools akmods)
        _install_
        sudo kmodgenca
        sudo mokutil --import /etc/pki/akmods/certs/public_key.der
        git clone https://github.com/CheariX/silverblue-akmods-keys
        cd silverblue-akmods-keys
        sudo bash setup.sh
        sudo rpm-ostree install akmods-keys-0.0.2-8.fc$(rpm -E %fedora).noarch.rpm
    fi
fi
zeninf "$msg036"