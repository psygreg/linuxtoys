#!/bin/bash
# name: Tailscale
# version: 1.0
# description: tailscale_desc
# icon: tailscale.png
# compat: ubuntu, debian, fedora, arch, cachy, suse

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
source "$SCRIPT_DIR/../../libs/helpers.lib"
sudo_rq
curl -fsSL https://tailscale.com/install.sh | bash