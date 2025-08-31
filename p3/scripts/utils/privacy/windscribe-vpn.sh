#!/bin/bash
# name: Windscribe VPN
# version: 1.0
# description: Windscribe VPN
# icon: windscribe.svg
# compat: ubuntu, debian, fedora, arch, cachy, suse

# --- Start of the script code ---
. /etc/os-release
SCRIPT_DIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
source "$SCRIPT_DIR/../../../libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/../../../libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/../../../libs/helpers.lib"
sudo_rq

if [[ "$ID_LIKE" =~ (ubuntu|debian) ]] || [[ "$ID" =~ (ubuntu|debian) ]]; then
	# Ubuntu/Debian installation
	cd /tmp
	wget -O windscribe.deb "https://windscribe.com/install/desktop/linux_deb_x64"
	sudo dpkg -i windscribe.deb
	sudo apt-get install -f -y
	rm -f windscribe.deb
elif [[ "$ID_LIKE" =~ (rhel|fedora) ]] || [[ "$ID" =~ (fedora|rhel) ]]; then
	# Fedora/RHEL installation
	cd /tmp
	wget -O windscribe.rpm "https://windscribe.com/install/desktop/linux_rpm_x64"
	if command -v rpm-ostree &>/dev/null; then
		# OSTree-based systems (Silverblue, etc.)
		rpm-ostree install windscribe.rpm
	else
		# Regular RPM-based systems - try dnf first, fallback to rpm
		if command -v dnf &>/dev/null; then
			sudo dnf install -y windscribe.rpm || sudo rpm -i windscribe.rpm
		else
			sudo rpm -i windscribe.rpm
		fi
	fi
	rm -f windscribe.rpm
elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" == *arch* ]] || [[ "$ID_LIKE" == *archlinux* ]]; then
	# Arch Linux installation
	cd /tmp
	wget -O windscribe.pkg.tar.zst "https://windscribe.com/install/desktop/linux_zst_x64"
	sudo pacman -U --noconfirm windscribe.pkg.tar.zst
	rm -f windscribe.pkg.tar.zst
elif [[ "$ID" =~ (suse|opensuse) ]] || [[ "$ID_LIKE" == *suse* ]]; then
	# openSUSE installation
	cd /tmp
	wget -O windscribe.rpm "https://windscribe.com/install/desktop/linux_rpm_opensuse_x64"
	sudo zypper install -y windscribe.rpm
	rm -f windscribe.rpm
else
    fatal "$msg077"
fi

