#!/bin/bash
# name: WireGuard
# version: 1.0
# description: WireGuard
# icon: wireguard.svg
# compat: ubuntu, debian, fedora, arch, cachy, suse, solus
# repo: https://www.wireguard.com

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_ubuntu || is_debian; then
	pkg_install wireguard
elif is_arch || is_cachy || is_solus || is_fedora || is_suse; then
	pkg_install wireguard-tools
else
    fatal "$msg077"
fi
