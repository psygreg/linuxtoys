#!/bin/bash
# NAME: ufw
# VERSION: 1.0
# DESCRIPTION: ufw_desc
# ICON: firewall.svg
# compat: ubuntu, debian, arch
# nocontainer

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../libs/linuxtoys.lib"
sudo_rq
_packages=(ufw gufw)
_install_
if command -v ufw &> /dev/null; then
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw enable
fi
zeninf $"The firewall has been configured and enabled."