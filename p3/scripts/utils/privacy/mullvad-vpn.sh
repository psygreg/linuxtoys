#!/bin/bash
# name: Mullvad VPN
# version: 1.0
# description: Mullvad VPN
# icon: mullvadvpn.svg
# compat: ubuntu, debian, fedora, arch, cachy, ostree, ublue

# --- Start of the script code ---
. /etc/os-release
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
sudo_rq
if [[ "$ID_LIKE" == *debian* ]] || [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "debian" ] || [ "$ID" == "ubuntu" ]; then
	sudo curl -fsSLo /usr/share/keyrings/mullvad-keyring.asc https://repository.mullvad.net/deb/mullvad-keyring.asc
	echo "deb [signed-by=/usr/share/keyrings/mullvad-keyring.asc arch=$( dpkg --print-architecture )] https://repository.mullvad.net/deb/stable stable main" | sudo tee /etc/apt/sources.list.d/mullvad.list
	sudo apt-get update
 	_packages=(mullvad-vpn)
	_install_
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora) ]]; then
	if command -v rpm-ostree &>/dev/null; then
		cd $HOME
		wget https://repository.mullvad.net/rpm/stable/mullvad.repo
		sudo install -o root -g root -m 644 mullvad.repo /etc/yum.repos.d/
		rpm-ostree refresh-md
	else
		sudo dnf config-manager addrepo --from-repofile=https://repository.mullvad.net/rpm/stable/mullvad.repo
	fi
	_packages=(mullvad-vpn)
	_install_
elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
	chaotic_aur_lib
	_packages=(mullvad-vpn)
	_install_
else
    fatal "$msg077"
fi
