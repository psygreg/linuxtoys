#!/bin/bash
# NAME: ufw
# VERSION: 1.0
# DESCRIPTION: ufw_desc
# ICON: firewall.svg
# compat: ubuntu, debian, arch
# nocontainer

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
pkg_install ufw gufw
if command -v ufw &> /dev/null; then
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    sudo ufw enable
fi
zeninf "$msg008"

