#!/bin/bash
# name: Express VPN
# version: 1.0
# description: Express VPN
# icon: expressvpn.svg
# compat: ubuntu, debian, fedora, arch, cachy

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
curl -fsSLo /tmp/express-instaler.run https://www.expressvpn.works/clients/linux/expressvpn-linux-universal-4.1.1.10039.run && bash /tmp/express-instaler.run && rm /tmp/express-instaler.run
