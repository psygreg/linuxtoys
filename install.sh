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
	if command -v rpm-ostree >/dev/null 2>&1 && [ -f /run/ostree-booted ]; then
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
			{ [ "$ID" = "rhel" ]; } && sudo subscription-manager repos --enable codeready-builder-for-rhel-$(rpm -E %rhel)-$(arch)-rpms && sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-$(rpm -E %rhel).noarch.rpm
			{ [[ "$ID_LIKE" = *rhel* ]] && [ "$ID" != "rhel" ]; } && sudo dnf config-manager --set-enabled crb && sudo dnf install epel-release
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
        if sudo rpm -U --nodeps --replacefiles --replacepkgs "/tmp/${_rpm_name}"; then
            dependencies=(
                bash git curl wget zenity python3 python3-gobject gtk3
                python3-requests python3-urllib3 python3-certifi
                libvte-2_91-0 typelib-1_0-Vte-2.91
            )
            for pkg in "${dependencies[@]}"; do
                sudo zypper --non-interactive install "${pkg}"
            done
            info "LinuxToys installed or updated!"
        else
            error "Installation failed (rpm)."
        fi
    else
        error "Failed to download: ${_rpm_name}"
    fi
}

osarch() {
    _pkg_dir="/tmp/linuxtoys/"
    if pacman -Qi linuxtoys-bin &>/dev/null; then
        sudo pacman -R --noconfirm linuxtoys-bin || error "Failed to remove existing linuxtoys-bin package."
    fi
    { pacman -Qi debugedit &>/dev/null || sudo pacman -S --noconfirm debugedit; } ||
        error "Failed to install makepkg dependency debugedit"
    { pacman -Qi fakeroot &>/dev/null || sudo pacman -S --noconfirm fakeroot; } ||
        error "Failed to install makepkg dependency fakeroot"
    rm -rf "${_pkg_dir}" # fix file permanence on /tmp on some arch distros
    mkdir -p "${_pkg_dir}"

    if curl -fsSL "${_pkg}" -o "${_pkg_dir}${_pkg_name}"; then
        cd "${_pkg_dir}" || error "Failed to enter build directory."
		if makepkg -s -f; then
			if sudo pacman -U --noconfirm "${_pkg_dir}linuxtoys-${_tag_name}-1-$(uname -m).pkg.tar.zst"; then
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

ossteamos() {
	local _appimage_dir _appimage_file _flatpak_scope _output

	[ -n "${_appimage:-}" ] || error "No AppImage was found in the latest LinuxToys release."
	[ -n "${_appimage_name:-}" ] || error "Could not determine the LinuxToys AppImage filename."

	if ! command -v flatpak >/dev/null 2>&1; then
		error "Flatpak is required to install LinuxToys on SteamOS."
	fi

	# Prefer the user's existing Flathub setup. If Flathub exists only system-wide,
	# use that scope instead, matching LinuxToys' normal Flatpak behavior.
	_flatpak_scope="--user"
	if flatpak remote-list --user --columns=name 2>/dev/null | grep -qx flathub; then
		:
	elif flatpak remote-list --system --columns=name 2>/dev/null | grep -qx flathub; then
		_flatpak_scope="--system"
	else
		flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo ||
			error "Failed to configure Flathub."
	fi

	if ! flatpak info "${_flatpak_scope}" it.mijorus.gearlever >/dev/null 2>&1; then
		if [ "${_flatpak_scope}" = "--system" ]; then
			sudo flatpak install --system -y flathub it.mijorus.gearlever ||
				error "Failed to install Gear Lever."
		else
			flatpak install --user -y flathub it.mijorus.gearlever ||
				error "Failed to install Gear Lever."
		fi
	fi

	_appimage_dir=$(mktemp -d "${TMPDIR:-/tmp}/linuxtoys-appimage.XXXXXX") ||
		error "Failed to create temporary AppImage directory."
	trap 'rm -rf -- "${_appimage_dir}"' EXIT
	_appimage_file="${_appimage_dir}/${_appimage_name}"

	printf "\e[0;36m[INFO]\e[m Downloading LinuxToys AppImage...\n"
	curl -fL --retry 3 "${_appimage}" -o "${_appimage_file}" ||
		error "Failed to download: ${_appimage_name}"
	chmod +x "${_appimage_file}" || error "Failed to make the AppImage executable."
	mkdir -p "${HOME}/AppImages" || error "Failed to create ${HOME}/AppImages."

	# Gear Lever's update/replace flow has proven unreliable for LinuxToys.
	# Remove an existing integrated LinuxToys AppImage first, mirroring
	# pkg_appimage_rm's systemd behavior, then perform a clean integration.
	local -a _installed_appimages=()
	local _installed_appimage
	while IFS= read -r _installed_appimage; do
		[ -n "${_installed_appimage}" ] && _installed_appimages+=("${_installed_appimage}")
	done < <(find "${HOME}/AppImages" -maxdepth 1 -type f -iname 'linuxtoys*.AppImage' -printf '%f\n' 2>/dev/null)

	if [ "${#_installed_appimages[@]}" -gt 1 ]; then
		error "Multiple LinuxToys AppImages were found in ${HOME}/AppImages; refusing to choose one automatically."
	elif [ "${#_installed_appimages[@]}" -eq 1 ]; then
		_installed_appimage="${_installed_appimages[0]}"
		printf "\e[0;36m[INFO]\e[m Removing existing LinuxToys AppImage...\n"
		(
			cd "${HOME}/AppImages" || exit 1
			echo "y" | flatpak run it.mijorus.gearlever --remove "${_installed_appimage}"
		) || error "Failed to remove existing LinuxToys AppImage: ${_installed_appimage}"

		if [ -e "${HOME}/AppImages/${_installed_appimage}" ] || [ -L "${HOME}/AppImages/${_installed_appimage}" ]; then
			error "Existing LinuxToys AppImage is still present after Gear Lever removal."
		fi
	fi

	printf "\e[0;36m[INFO]\e[m Integrating LinuxToys with Gear Lever...\n"
	_output=$(echo "y" | flatpak run it.mijorus.gearlever --integrate "${_appimage_file}" 2>&1) || {
		printf '%s\n' "${_output}"
		error "Failed to integrate LinuxToys AppImage with Gear Lever."
	}

	info "LinuxToys installed or updated!"
}

ossolus() {
	if curl -fsSL "${_eopkg}" -o "/tmp/${_eopkg_name}"; then
		if command -v eopkg >/dev/null 2>&1; then
			if sudo eopkg install -y "/tmp/${_eopkg_name}"; then
				info "LinuxToys installed or updated!"
			else
				error "Installation failed (eopkg)."
			fi
		else
			error "eopkg command not found on Solus system."
		fi
	else
		error "Failed to download: ${_eopkg_name}"
	fi
}

manjaro() {
    { sudo pamac build linuxtoys-bin && info "LinuxToys installed or updated!"; } || error "Failed to download: ${_pkg_name}"
}

installer() {
	# Try GitHub first as primary source
	printf "\e[0;36m[INFO]\e[m Fetching latest release from GitHub...\n"
	_api=$(curl -fsSL "https://api.github.com/repos/psygreg/linuxtoys/releases/latest" 2>/dev/null)

	# If GitHub fails, fallback to Gitea server
	if [ -z "${_api}" ]; then
		printf "\e[0;33m[WARN]\e[m GitHub unavailable, trying Gitea server at git.linux.toys...\n"
		_api=$(curl -fsSL "https://git.linux.toys/api/v1/repos/psygreg/linuxtoys/releases/latest" 2>/dev/null)
	fi

	if [ -z "${_api}" ]; then
		error "Failed to fetch release information from GitHub and git.linux.toys"
	fi

	_tag_name=$(echo "${_api}" | grep -Pio '"tag_name":\s*"\K[^"]+')

	_appimage=$(echo "${_api}" | grep -Pio '"browser_download_url":\s*"\K[^"]+?\.AppImage' | head -n1)
	_appimage_name=$(basename "${_appimage}")

	_rpm=$(echo "${_api}" | grep -Pio '"browser_download_url":\s*"\K[^"]+?\.rpm')
	_rpm_name=$(basename "${_rpm}")

	_deb=$(echo "${_api}" | grep -Pio '"browser_download_url":\s*"\K[^"]+?\.deb')
	_deb_name=$(basename "${_deb}")

	_pkg=$(echo "${_api}" | grep -Pio '"browser_download_url":\s*"\K[^"]+?/PKGBUILD')
	# _pkg_tarball=$(echo "${_api}" | grep -Pio '"browser_download_url":\s*"\K[^"]+?\.tar.xz')
	_pkg_name=$(basename "${_pkg}")
	# _pkg_tarball_name=$(basename "${_pkg_tarball}")

	_eopkg=$(echo "${_api}" | grep -Pio '"browser_download_url":\s*"\K[^"]+?\.eopkg')
	_eopkg_name=$(basename "${_eopkg}")

	ostree

	if [ -r /etc/os-release ]; then
		# shellcheck disable=SC1091
		. /etc/os-release
	else
		error "Unsupported operating system (no /etc/os-release)."
	fi

	case "${ID:-}" in
		debian|ubuntu|deepin) osdeb ;;
		fedora|rhel|centos|rocky|almalinux) osrpm ;;
		suse|opensuse) ossuse ;;
		manjaro|biglinux|bigcommunity) manjaro;;
		steamos) ossteamos ;;
		arch|cachyos|artix) osarch ;;
		solus) ossolus ;;
	esac

	case "${ID_LIKE:-}" in
		*debian*|*ubuntu*) osdeb ;;
		*rhel*|*fedora*) osrpm ;;
		*manjaro*) manjaro ;;
		*suse*) ossuse ;;
		*arch*)
			if [ "${ID:-}" = "steamos" ]; then
				ossteamos
			else
				osarch
			fi
			;;
	esac

	error "Unsupported operating system."
}

if [ -t 0 ] && [ "${LINUXTOYS_NONINTERACTIVE:-0}" != "1" ]; then
    header
    printf 'Do you wish to install or update LinuxToys? (y/n): '
    read -r _answer < /dev/tty
    if [ "${_answer}" != "y" ]; then info "Installation aborted."; fi
    installer
else
    header
    installer
fi
