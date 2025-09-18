#!/bin/bash
# name: WireGuard
# version: 1.0
# description: WireGuard
# icon: wireguard.svg
# compat: ubuntu, debian, fedora, arch, cachy, suse

# --- Start of the script code ---
. /etc/os-release
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
if [[ "$ID_LIKE" =~ (ubuntu|debian) ]];then
	_packages=(wireguard)
	_install_
elif [[ "$ID_LIKE" =~ (suse|rhel|fedora) ]];then
	_packages=(wireguard-tools)
	_install_
elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
	_packages=(wireguard-tools)
	_install_
else
    fatal "$msg077"
fi
