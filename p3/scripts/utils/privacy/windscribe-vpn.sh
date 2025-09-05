#!/bin/bash
# name: Windscribe VPN
# version: 1.0
# description: Windscribe VPN
# icon: windscribe.svg

# --- Start of the script code ---
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../../libs/linuxtoys.lib"
sudo_rq
cd $HOME
if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [[ "$ID" =~ (ubuntu|debian) ]]; then
	# Ubuntu/Debian installation
	wget -O windscribe.deb "https://windscribe.com/install/desktop/linux_deb_x64"
	sudo dpkg -i windscribe.deb
	sudo apt-get install -f -y
	rm -f windscribe.deb
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora|rhel) ]]; then
	# Fedora/RHEL installation
	wget -O windscribe.rpm "https://windscribe.com/install/desktop/linux_rpm_x64"
	if command -v rpm-ostree &>/dev/null; then
		# OSTree-based systems (Silverblue, etc.)
		sudo rpm-ostree install -yA windscribe.rpm
	else
		sudo dnf install -y windscribe.rpm
	fi
	rm -f windscribe.rpm
elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
	# Arch Linux installation
	wget -O windscribe.pkg.tar.zst "https://windscribe.com/install/desktop/linux_zst_x64"
	sudo pacman -U --noconfirm windscribe.pkg.tar.zst
	rm -f windscribe.pkg.tar.zst
elif [[ "$ID" =~ (suse|opensuse) ]] || [[ "$ID_LIKE" == *suse* ]]; then
	# openSUSE installation
	wget -O windscribe.rpm "https://windscribe.com/install/desktop/linux_rpm_opensuse_x64"
	sudo zypper install -y windscribe.rpm
	rm -f windscribe.rpm
else
    fatal $"This script is not compatible with your operating system."
fi
zeninf $"Operations completed."