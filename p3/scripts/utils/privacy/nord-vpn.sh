#!/bin/bash
# name: Nord VPN
# version: 1.0
# description: Nord VPN
# icon: nordvpn.svg
# compat: ubuntu, debian, fedora, arch, cachy, suse
# repo: https://nordvpn.com

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_debian || is_ubuntu || is_suse || is_fedora; then
	sh <(wget -qO - https://downloads.nordcdn.com/apps/linux/install.sh) -p nordvpn-gui -n
elif is_arch || is_cachyos; then
	pkg_install nordvpn-bin
else
    fatal "$msg077"
fi
