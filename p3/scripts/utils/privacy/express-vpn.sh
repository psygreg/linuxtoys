#!/bin/bash
# name: Express VPN
# version: 1.0
# description: Express VPN
# icon: expressvpn.svg
# compat: ubuntu, debian, fedora, arch, cachy
# repo: https://www.expressvpn.com
# revert: no

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
curl -fsSLo /tmp/express-instaler.run https://www.expressvpn.works/clients/linux/expressvpn-linux-universal-4.1.1.10039.run && bash /tmp/express-instaler.run && rm /tmp/express-instaler.run
