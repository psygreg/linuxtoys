#!/bin/bash
# name: Astah Pro
# version: 1.0
# description: astapro_desc
# icon: astahpro.png
# repo: https://astah.net/products/astah-professional/
# needed: adoptium-jdk
# compat: debian, ubuntu, fedora

source "$SCRIPT_DIR/libs/linuxtoys.lib"
_lang_
source "$SCRIPT_DIR/libs/lang/${langfile}.lib"
source "$SCRIPT_DIR/libs/helpers.lib"

DEB_LINK="https://members.change-vision.com/download/files/astah_professional/latest/linux_deb"
RPM_LINK="https://members.change-vision.com/download/files/astah_professional/latest/linux_rpm"

sudo_rq

if is_debian;then
    _deb="$(curl -s -o /dev/null -w "%{redirect_url}\n" "${DEB_LINK}")"
    _deb_name=$(basename ${_deb})

    if curl -fsSL "${_deb}" -o "/tmp/${_deb_name}"; then
		sudo apt update || true
		if sudo apt install -y "/tmp/${_deb_name}"; then
			zeninf "Astah Pro installed successfully!"
		else
			fatal "Installation failed (apt)."
		fi
	else
		fatal "Failed to download: ${_deb_name}"
	fi
elif is_fedora;then
    _rpm="$(curl -s -o /dev/null -w "%{redirect_url}\n" "${RPM_LINK}")"
    _rpm_name=$(basename ${_rpm})

    if curl -fsSL "${_rpm}" -o "/tmp/${_rpm_name}"; then
		if command -v dnf >/dev/null 2>&1; then
			if sudo dnf install -y "/tmp/${_rpm_name}"; then
				zeninf "Astah Pro installed successfully!"
			else
				fatal "Installation failed (dnf)."
			fi
		else
			if sudo yum install -y "/tmp/${_rpm_name}"; then
				zeninf "Astah Pro installed successfully!"
			else
				fatal "Installation failed (yum)."
			fi
		fi
	else
		fatal "Failed to download: ${_rpm_name}"
	fi
else
    fatal "Unsupported distribution"
fi