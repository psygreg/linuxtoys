#!/bin/bash
header() {
	echo "  _      _               _______               "
	echo " | |    (_)             |__   __|              "
	echo " | |     _ _ __  _   ___  _| | ___  _   _ ___  "
	echo " | |    | | '_ \| | | \ \/ / |/ _ \| | | / __| "
	echo " | |____| | | | | |_| |>  <| | (_) | |_| \__ \ "
	echo " |______|_|_| |_|\__,_/_/\_\_|\___/ \__, |___/ "
	echo "                                     __/ |     "
	echo "                                    |___/      "
	echo "                QUICK-INSTALLER                "
	echo
}

info() { printf "\e[0;32m[INFO]\e[m %s\n" "${1}"; exit 0; }

error() { printf "\e[0;31m[ERROR]\e[m %s\n" "${1}"; exit 1; }

ostree() {
	if command -v rpm-ostree >/dev/null 2>&1; then
		if curl -fsSL "${_rpm}" -o "/tmp/${_rpm_name}"; then
			if rpm -qi linuxtoys >/dev/null 2>&1; then
				if ! sudo rpm-ostree remove linuxtoys; then
					error "Failed to remove existing linuxtoys."
				fi
			fi

			if sudo rpm-ostree install "/tmp/${_rpm_name}"; then
				info "LinuxToys installed or updated!"
			else
				error "Installation failed (rpm-ostree)."
			fi
		else
			error "Failed to download: ${_rpm_name}"
		fi
	fi
}

osdeb() {
	if curl -fsSL "${_deb}" -o "/tmp/${_deb_name}"; then
		sudo apt update || true
		if sudo apt install -y "/tmp/${_deb_name}"; then
			info "LinuxToys installed or updated!"
		else
			error "Installation failed (apt)."
		fi
	else
		error "Failed to download: ${_deb_name}"
	fi
}

osrpm() {
	if curl -fsSL "${_rpm}" -o "/tmp/${_rpm_name}"; then
		if command -v dnf >/dev/null 2>&1; then
			if sudo dnf install -y "/tmp/${_rpm_name}"; then
				info "LinuxToys installed or updated!"
			else
				error "Installation failed (dnf)."
			fi
		else
			if sudo yum install -y "/tmp/${_rpm_name}"; then
				info "LinuxToys installed or updated!"
			else
				error "Installation failed (yum)."
			fi
		fi
	else
		error "Failed to download: ${_rpm_name}"
	fi
}

ossuse() {
	if curl -fsSL "${_rpm}" -o "/tmp/${_rpm_name}"; then
		if sudo rpm -i --nodeps "/tmp/${_rpm_name}"; then
			dependencies=(bash git curl wget zenity python3 python3-gobject gtk3 python3-requests python3-urllib3 python3-certifi libvte-2_91-0 typelib-1_0-Vte-2.91)
			for pkg in "${dependencies[@]}"; do
				sudo zypper --non-interactive install "${pkg}"
			done
			info "LinuxToys installed or updated!"
		else
			error "Installation failed (zypper)."
		fi
	else
		error "Failed to download: ${_rpm_name}"
	fi
}

osarch() {
	_pkg_dir="/tmp/linuxtoys/"
	mkdir -p ${_pkg_dir}
	if curl -fsSL "${_pkg}" -o "${_pkg_dir}${_pkg_name}"; then
		if makepkg -fcCd OPTIONS=-debug -D "${_pkg_dir}"; then
			if sudo pacman -U --noconfirm ${_pkg_dir}linuxtoys-*.pkg.tar.zst; then
				info "LinuxToys installed or updated!"
			else
				error "Installation failed (pacman)."	
			fi
		else
			error "Build failed (makepkg)."
		fi
	else
		error "Failed to download: ${_pkg_name}"
	fi
}

installer() {
	_api="$(curl -fsSL "https://api.github.com/repos/psygreg/linuxtoys/releases/latest")"
	if [ -z "${_api}" ] ; then error "Failed to get api"; fi

	_rpm=$(echo "${_api}" | grep -Pio '(?<=browser_download_url": ")([^"]+?\.rpm)(?=")')
	_rpm_name=$(basename "${_rpm}")

	_deb=$(echo "${_api}" | grep -Pio '(?<=browser_download_url": ")([^"]+?\.deb)(?=")')
	_deb_name=$(basename "${_deb}")

	_pkg=$(echo "${_api}" | grep -Pio '(?<=browser_download_url": ")([^"]+?/PKGBUILD)(?=")')
	_pkg_name=$(basename "${_pkg}")

	ostree

	if [ -r /etc/os-release ]; then
		# shellcheck disable=SC1091
		. /etc/os-release
	else
		error "Unsupported operating system (no /etc/os-release)."
	fi

	case "${ID:-}" in
		debian|ubuntu) osdeb ;;
		fedora|rhel|centos|rocky|almalinux) osrpm ;;
		suse|opensuse) ossuse ;;
		arch|cachyos) osarch ;;
	esac

	case "${ID_LIKE:-}" in
		*debian*|*ubuntu*) osdeb ;;
		*rhel*|*fedora*) osrpm ;;
		*suse*) ossuse ;;
		*arch*) osarch;;
	esac

	error "Unsupported operating system."
}

if [ -t 0 ]; then
	header
	printf 'Do you wish to install or update LinuxToys? (y/n): '
	read -r _answer < /dev/tty
	if [ "${_answer}" != "y" ]; then info "Installation aborted."; fi
	installer
else
	header
	yes | installer
fi