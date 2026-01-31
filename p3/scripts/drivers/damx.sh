#!/bin/bash
# name: Acer Manager
# version: 1.0
# description: damx_desc
# icon: damx.png
# reboot: yes
# repo: https://github.com/PXDiv/Div-Acer-Manager-Max

# --- Start of the script code ---
source "$SCRIPT_DIR/libs/linuxtoys.lib"
source "$SCRIPT_DIR/libs/helpers.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"

_gh_user="PXDiv"
_gh_repo="Div-Acer-Manager-Max"

_choice=$(zenity --list --title="DAMX Suite Installer" \
--width=500 --height=380 \
--radiolist \
--column="Choices" --column="num" --column="Options" \
--hide-column=2 \
TRUE  1 "$msg296" \
FALSE 2 "$msg297" \
FALSE 3 "$msg298" \
FALSE 4 "$msg299" \
FALSE 5 "$msg300")

[ -n "${_choice}" ] || { zeninf "$msg281"; exit 0; }

_vers=$(curl https://github.com/${_gh_user}/${_gh_repo}/releases/latest -sw '%{redirect_url}' | awk -F'/' '{print $NF}')
_tarb=($(curl -fsSL https://github.com/${_gh_user}/${_gh_repo}/releases/expanded_assets/${_vers} | grep -Pio '(?<=href=")([^"]+.tar.xz)'))
curl -fsSL "https://github.com/${_tarb}" -o- | tar -xvJf -  --strip-components=1 --one-top-level="/tmp/damx/" && {
	sudo_rq
	[ "${_choice}" -eq 1 -o "${_choice}" -eq 4 ] && {
		if [[ "$ID" =~ ^(debian|ubuntu)$ ]] || [[ "$ID_LIKE" =~ (debian|ubuntu) ]]; then
			_packages=(make build-essential)
		elif [[ "$ID" =~ ^(arch|cachyos)$ ]] || [[ "$ID_LIKE" =~ (arch|archlinux) ]]; then
			_k=($(uname -r | grep -o -E 'rt-lts|lts|zen|rt|hardened'))
			_packages=(base-devel linux${_k:+-${_k}}-headers)
		elif [[ "$ID" =~ ^(rhel|fedora|suse)$ ]] || [[ "$ID_LIKE" =~ (rhel|fedora|suse) ]]; then
			_packages=(make gcc kernel-headers kernel-devel)
		fi
		_install_
	}
	cd /tmp/damx/
	echo -e "${_choice}\nq\nq\n" | sudo bash setup.sh && { zeninf "$msg018"; } || { fatal "Acer Manager installation unsuccessful"; }
}