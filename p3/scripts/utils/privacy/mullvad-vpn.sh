#!/bin/bash
# name: Mullvad VPN
# version: 1.0
# description: Mullvad VPN
# icon: mullvadvpn.svg
# compat: ubuntu, debian, fedora, arch, cachy, ostree, ublue
# repo: https://mullvad.net/vpn

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
sudo_rq
if is_debian || is_ubuntu; then
	sudo curl -fsSLo /usr/share/keyrings/mullvad-keyring.asc https://repository.mullvad.net/deb/mullvad-keyring.asc
	echo "deb [signed-by=/usr/share/keyrings/mullvad-keyring.asc arch=$( dpkg --print-architecture )] https://repository.mullvad.net/deb/stable stable main" | sudo tee /etc/apt/sources.list.d/mullvad.list
	sudo apt-get update
elif is_fedora || is_ostree; then
	if command -v rpm-ostree &>/dev/null; then
		prep_tmp
		wget https://repository.mullvad.net/rpm/stable/mullvad.repo
		sudo install -o root -g root -m 644 mullvad.repo /etc/yum.repos.d/
		rpm-ostree refresh-md
	else
		sudo dnf config-manager addrepo --from-repofile=https://repository.mullvad.net/rpm/stable/mullvad.repo
	fi
fi
pkg_install mullvad-vpn