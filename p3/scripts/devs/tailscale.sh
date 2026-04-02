#!/bin/bash
# name: Tailscale
# version: 1.0
# description: tailscale_desc
# icon: tailscale.png
# compat: ubuntu, debian, fedora, arch, cachy, suse, solus

# --- Start of the script code ---
. /etc/os-release
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
if is_solus; then
    _packages=(tailscale)
    _install_
    sudo tailscale up # prompts user to login to their Tailscale account and connect to the network
else
    curl -fsSL https://tailscale.com/install.sh | bash
fi