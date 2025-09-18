#!/bin/bash
# name: IVPN
# version: 1.0
# description: IVPN
# icon: ivpn.svg
# compat: ubuntu, debian, fedora, ostree, ublue

# --- Start of the script code ---
. /etc/os-release
#SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
sudo_rq
if [[ "$ID_LIKE" == *debian* ]] || [ "$ID" == "debian" ]; then
	# Add IVPN's GPG key
	curl -fsSL https://repo.ivpn.net/stable/debian/generic.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/ivpn-archive-keyring.gpg > /dev/null
	# Set Appropriate Permissions for GPG key
	sudo chown root:root /usr/share/keyrings/ivpn-archive-keyring.gpg && sudo chmod 644 /usr/share/keyrings/ivpn-archive-keyring.gpg
	# Add the IVPN repository
	curl -fsSL https://repo.ivpn.net/stable/debian/generic.list | sudo tee /etc/apt/sources.list.d/ivpn.list
	# Set Appropriate Permissions for Repository
	sudo chown root:root /etc/apt/sources.list.d/ivpn.list && sudo chmod 644 /etc/apt/sources.list.d/ivpn.list
	# Update APT repo info
	sudo apt update
	# Install IVPN software (CLI and UI)
	_packages=(ivpn-ui)
	_install_
elif [[ "$ID_LIKE" == *ubuntu* ]] || [ "$ID" == "ubuntu" ]; then
	# Add IVPN's GPG key
	curl -fsSL https://repo.ivpn.net/stable/ubuntu/generic.gpg | gpg --dearmor | sudo tee /usr/share/keyrings/ivpn-archive-keyring.gpg > /dev/null
	# Set Appropriate Permissions for GPG key
	sudo chown root:root /usr/share/keyrings/ivpn-archive-keyring.gpg && sudo chmod 644 /usr/share/keyrings/ivpn-archive-keyring.gpg
	# Add the IVPN repository
	curl -fsSL https://repo.ivpn.net/stable/ubuntu/generic.list | sudo tee /etc/apt/sources.list.d/ivpn.list
	# Set Appropriate Permissions for Repository
	sudo chown root:root /etc/apt/sources.list.d/ivpn.list && sudo chmod 644 /etc/apt/sources.list.d/ivpn.list
	# Update APT repo info
	sudo apt update
	# Install IVPN software (CLI and UI)
	_packages=(ivpn-ui)
	_install_
elif [[ "$ID_LIKE" == *fedora* ]] || [ "$ID" == "fedora" ]; then
	if command -v rpm-ostree &>/dev/null; then
		cd $HOME
		wget https://repo.ivpn.net/stable/fedora/generic/ivpn.repo
		sudo install -o root -g root -m 644 ivpn.repo /etc/yum.repos.d/
		rpm-ostree refresh-md
	else
		sudo dnf config-manager addrepo --from-repofile=https://repo.ivpn.net/stable/fedora/generic/ivpn.repo
	fi
	# Install IVPN software (CLI and UI)
	_packages=(ivpn-ui)
	_install_
else
    fatal "$msg077"
fi
