#!/bin/bash
# name: Tailscale
# version: 1.0
# description: tailscale_desc
# icon: tailscale.png
# compat: ubuntu, debian, fedora, arch, cachy, suse, solus
# revert: solus

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
sudo_rq
if is_solus; then
    pkg_install tailscale
    sudo tailscale up # prompts user to login to their Tailscale account and connect to the network
else
    curl -fsSL https://tailscale.com/install.sh | bash
fi