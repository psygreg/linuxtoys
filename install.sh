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

# Delegate ISA policy to the application; never maintain installer alias tables.
architecture_prepare() {
    command -v python3 >/dev/null 2>&1 || error "Python 3 is required for safe architecture validation."
    _architecture_work=$(mktemp -d "${TMPDIR:-/tmp}/linuxtoys-preflight.XXXXXX") || error "Cannot stage preflight."
    trap 'rm -rf -- "${_architecture_work}"' EXIT
    local source_dir revision file
    source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)
    # Only a user-owned checkout may supply local executable validation code.
    # A downloaded installer in /tmp must not import an attacker's sibling p3/.
    if [ -e "$source_dir/.git" ] && [ -f "$source_dir/p3/app/architecture_cli.py" ] &&
       python3 - "$source_dir" <<'PYLOCAL'
import os, pathlib, stat, sys
root = pathlib.Path(sys.argv[1]).resolve()
paths = [root, root / 'p3', root / 'p3/app', root / 'p3/app/__init__.py']
paths += [root / 'p3/app' / name for name in (
    'architecture.py', 'architecture_cli.py', 'architecture_files.py', 'architecture_flatpak.py')]
paths += [root / 'p3/libs', root / 'p3/libs/packages.bash']
for path in paths:
    metadata = path.lstat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o022 or stat.S_ISLNK(metadata.st_mode):
        raise SystemExit(1)
PYLOCAL
    then
        _architecture_cli="$source_dir/p3/app/architecture_cli.py"
        _package_library="$source_dir/p3/libs/packages.bash"
    else
        revision=$(python3 -c 'import json,sys; from urllib.parse import quote; print(quote(json.load(sys.stdin)["tag_name"], safe=""))' <<< "$_api") || error "Release has no source tag."
        revision=$(curl -fsSL "https://api.github.com/repos/psygreg/linuxtoys/commits/$revision" | python3 -c 'import json,re,sys; s=json.load(sys.stdin)["sha"]; assert re.fullmatch("[0-9a-f]{40}",s); print(s)') || error "Cannot resolve immutable release source."
        mkdir -p "$_architecture_work/app" || error "Cannot stage architecture helper."
        : > "$_architecture_work/app/__init__.py"
        for file in architecture.py architecture_files.py architecture_flatpak.py architecture_cli.py; do
            curl -fsSL "https://raw.githubusercontent.com/psygreg/linuxtoys/$revision/p3/app/$file" -o "$_architecture_work/app/$file" || error "Release lacks architecture validation; use a qualified release."
        done
        _architecture_cli="$_architecture_work/app/architecture_cli.py"
        mkdir -p "$_architecture_work/libs" || error "Cannot stage package guards."
        _package_library="$_architecture_work/libs/packages.bash"
        curl -fsSL "https://raw.githubusercontent.com/psygreg/linuxtoys/$revision/p3/libs/packages.bash" -o "$_package_library" || error "Release lacks package guards; use a qualified release."
    fi
    python3 "$_architecture_cli" label host >/dev/null || error "Unsupported host architecture."
    ( _lt_load_package_guards ) || error "Release lacks the required bounded package guards."
    printf '%s' "$_api" > "$_architecture_work/release.json"
}

architecture_verify() {
    python3 - "$_architecture_work/sha256sums.txt" "$1" <<'PYHASH' || error "Release checksum validation failed."
import hashlib, pathlib, sys
path = pathlib.Path(sys.argv[2])
records = [line.split() for line in pathlib.Path(sys.argv[1]).read_text().splitlines()]
expected = [row[0] for row in records if len(row) == 2 and row[1].lstrip("*") == path.name]
if len(expected) != 1:
    raise SystemExit("Missing or ambiguous release checksum")
digest = hashlib.sha256()
with path.open("rb") as source:
    for chunk in iter(lambda: source.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != expected[0]:
    raise SystemExit("Release checksum mismatch")
PYHASH
    python3 "$_architecture_cli" files "$1" || error "Incompatible or unverified release payload."
}

# The same library owns lock observation and bounded retries in all launch
# modes. A private subshell prevents its definitions from replacing this
# installer's exit-on-success info(), or the background updater's helpers.
_lt_load_package_guards() {
    unset LINUXTOYS_PACKAGE_GUARD_API _PKG_GUARD_L10N_DONE
    # shellcheck source=p3/libs/packages.bash
    source "$_package_library" || return "$?"
    [[ "${LINUXTOYS_PACKAGE_GUARD_API:-}" == 2 ]] || {
        printf '%s\n' "Release lacks the required bounded package guards." >&2
        return 1
    }
}

_lt_installer_transaction() (
    local family="$1"
    shift
    _lt_load_package_guards || return "$?"
    "${family}_transaction" "$@"
)

# Noninteractive self-updates must not hang on a terminal password prompt.
# Interactive installs keep sudo's ordinary authentication behavior.
_lt_installer_sudo() {
    if [[ "${LINUXTOYS_NONINTERACTIVE:-0}" == 1 ]]; then
        sudo -n "$@"
    else
        sudo "$@"
    fi
}

osdeb() {
	if curl -fsSL "${_deb}" -o "${_architecture_work}/${_deb_name}"; then
        architecture_verify "${_architecture_work}/${_deb_name}"
		_lt_installer_transaction apt _lt_installer_sudo apt update || return "$?"
		if _lt_installer_transaction apt _lt_installer_sudo apt install -y "${_architecture_work}/${_deb_name}"; then
			info "LinuxToys installed or updated!"
		else
			return "$?"
		fi
	else
		error "Failed to download: ${_deb_name}"
	fi
}

osrpm() {
	if curl -fsSL "${_rpm}" -o "${_architecture_work}/${_rpm_name}"; then
        architecture_verify "${_architecture_work}/${_rpm_name}"
		if command -v dnf >/dev/null 2>&1; then
            if [[ "$ID" == rhel ]]; then
                _lt_installer_sudo subscription-manager repos --enable "codeready-builder-for-rhel-$(rpm -E %rhel)-$(arch)-rpms" || return "$?"
                _lt_installer_transaction dnf _lt_installer_sudo dnf install -y "https://dl.fedoraproject.org/pub/epel/epel-release-latest-$(rpm -E %rhel).noarch.rpm" || return "$?"
            elif [[ "$ID_LIKE" == *rhel* ]]; then
                _lt_installer_sudo dnf config-manager --set-enabled crb || return "$?"
                _lt_installer_transaction dnf _lt_installer_sudo dnf install -y epel-release || return "$?"
            fi
			if _lt_installer_transaction dnf _lt_installer_sudo dnf install -y "${_architecture_work}/${_rpm_name}"; then
				info "LinuxToys installed or updated!"
			else
				return "$?"
			fi
		else
			if _lt_installer_transaction dnf _lt_installer_sudo yum install -y "${_architecture_work}/${_rpm_name}"; then
				info "LinuxToys installed or updated!"
			else
				return "$?"
			fi
		fi
	else
		error "Failed to download: ${_rpm_name}"
	fi
}

ossuse() {
    if curl -fsSL "${_rpm}" -o "${_architecture_work}/${_rpm_name}"; then
        architecture_verify "${_architecture_work}/${_rpm_name}"
        if _lt_installer_transaction zypper _lt_installer_sudo zypper --non-interactive install "${_architecture_work}/${_rpm_name}"; then
            dependencies=(
                bash git curl wget zenity python3 python3-gobject gtk3
                python3-requests python3-urllib3 python3-certifi util-linux
                libvte-2_91-0 typelib-1_0-Vte-2.91 libappstream5 typelib-1_0-AppStream-1.0
                AppStream adwaita-icon-theme libzypp-plugin-appdata
            )
            for pkg in "${dependencies[@]}"; do
                _lt_installer_transaction zypper _lt_installer_sudo zypper --non-interactive install "${pkg}" || return "$?"
            done
            info "LinuxToys installed or updated!"
        else
            return "$?"
        fi
    else
        error "Failed to download: ${_rpm_name}"
    fi
}

osarch() {
    [ -n "${_pkg:-}" ] || error "No Arch Linux package was found in the latest LinuxToys release."
    [ -n "${_pkg_name:-}" ] || error "Could not determine the LinuxToys Arch package filename."

    curl -fL --retry 3 "${_pkg}" -o "$_architecture_work/${_pkg_name}" || error "Package download failed."
    architecture_verify "$_architecture_work/${_pkg_name}"
    if pacman -Qi linuxtoys-bin &>/dev/null; then
        _lt_installer_transaction pacman _lt_installer_sudo pacman -R --noconfirm linuxtoys-bin || return "$?"
    fi

    if [ -f "$_architecture_work/${_pkg_name}" ]; then
        if [ "$ID" = "cachyos" ]; then
            dependencies=(
                bash git curl wget zenity appstream archlinux-appstream-data
                python python-gobject python-requests gtk3 vte3 sudo util-linux
                webp-pixbuf-loader
            )
            for pkg in "${dependencies[@]}"; do
                _lt_installer_transaction pacman _lt_installer_sudo pacman -S --noconfirm --needed "${pkg}" || return "$?"
            done
        fi
        if _lt_installer_transaction pacman _lt_installer_sudo pacman -U --noconfirm "${_architecture_work}/${_pkg_name}"; then
            info "LinuxToys installed or updated!"
        else
            return "$?"
        fi
    else
        error "Failed to download: ${_pkg_name}"
    fi
}

osappimage() {
	local _appimage_dir _appimage_file _flatpak_scope _output

	[ -n "${_appimage:-}" ] || error "No AppImage was found in the latest LinuxToys release."
	[ -n "${_appimage_name:-}" ] || error "Could not determine the LinuxToys AppImage filename."

    _appimage_dir="$_architecture_work/appimage"
    mkdir -p "$_appimage_dir" || error "Cannot stage AppImage."
    _appimage_file="${_appimage_dir}/${_appimage_name}"
    curl -fL --retry 3 "${_appimage}" -o "${_appimage_file}" || error "AppImage download failed."
    architecture_verify "${_appimage_file}"

	if ! command -v flatpak >/dev/null 2>&1; then
		error "Flatpak is required to install the LinuxToys AppImage on this system."
	fi

	# Migration: hosts that installed LinuxToys through rpm-ostree layering
	# carry a native copy whose desktop entry would conflict with the
	# AppImage integration. Remove it before integrating the new one.
	if command -v rpm-ostree >/dev/null 2>&1 && [ -f /run/ostree-booted ] &&
		rpm -qi linuxtoys >/dev/null 2>&1; then
		printf "\e[0;36m[INFO]\e[m Removing existing rpm-ostree layered LinuxToys...\n"
		sudo rpm-ostree remove linuxtoys ||
			printf "\e[0;33m[WARN]\e[m Failed to remove the layered LinuxToys package; its desktop entry may keep appearing alongside the AppImage.\n"
	fi

	# Solus native packages can leave a conflicting desktop entry behind when
	# the AppImage is integrated. Remove the eopkg installation first.
	if [ "${ID:-}" = "solus" ] && command -v eopkg >/dev/null 2>&1 &&
		eopkg list-installed linuxtoys >/dev/null 2>&1; then
		printf "\e[0;36m[INFO]\e[m Removing existing eopkg LinuxToys installation...\n"
		sudo eopkg remove -y linuxtoys ||
			error "Failed to remove the existing eopkg LinuxToys installation."
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
			# --yes skips Gear Lever's prompt (the piped "y" covers older CLI
			# builds without it); filter its benign GLib sandbox warnings the
			# same way packages.bash's _gearlever_filter_output does.
			# Absolute path: Gear Lever's CLI matches the file argument by exact
			# string equality against the integrated desktop entry's path, so a
			# bare name never matches even with cwd inside ~/AppImages.
			_output=$(echo "y" | flatpak run it.mijorus.gearlever --remove --yes "${HOME}/AppImages/${_installed_appimage}" 2>&1) || exit $?
			printf '%s\n' "${_output}" | grep -vE '^\*\* \([^)]+\): |^Gtk-Message: ' || true
		) || error "Failed to remove existing LinuxToys AppImage: ${_installed_appimage}"

		if [ -e "${HOME}/AppImages/${_installed_appimage}" ] || [ -L "${HOME}/AppImages/${_installed_appimage}" ]; then
			error "Existing LinuxToys AppImage is still present after Gear Lever removal."
		fi
	fi

	printf "\e[0;36m[INFO]\e[m Integrating LinuxToys with Gear Lever...\n"
	_output=$(echo "y" | flatpak run it.mijorus.gearlever --integrate --yes "${_appimage_file}" 2>&1) || {
		printf '%s\n' "${_output}" | grep -vE '^\*\* \([^)]+\): |^Gtk-Message: ' || true
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
    osarch
}

requires_appimage() {
    # rpm-ostree immutable systems use the AppImage route as well: the native
    # package would have to be layered with rpm-ostree, which the AppImage
    # (via Gear Lever) avoids entirely. Mirrors the app's ostree/ublue keys.
    if command -v rpm-ostree >/dev/null 2>&1 && [ -f /run/ostree-booted ]; then
        return 0
    fi
    local distro_id="${ID,,}" distro_like=" ${ID_LIKE,,} "
    local distro_variant="${VARIANT_ID,,} ${VARIANT,,} ${NAME,,} ${PRETTY_NAME,,}"

    case "$distro_id" in
        steamos|gnomeos|kde-linux|dakota|bluefin-dakota) return 0 ;;
        bluefin)
            [[ "$distro_variant" == *dakota* || "$distro_like" == *" gnomeos "* ]] && return 0
            ;;
    esac
    [[ "$distro_like" == *" gnomeos "* ]]
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

    architecture_prepare
    _checksum_url=$(python3 -c 'import json,sys; a=[x["browser_download_url"] for x in json.load(sys.stdin).get("assets",[]) if x.get("name")=="sha256sums.txt"]; assert len(a)==1 and a[0].startswith("https://"); print(a[0])' <<< "$_api") || error "Release has no unique checksum manifest."
    curl -fsSL "$_checksum_url" -o "$_architecture_work/sha256sums.txt" || error "Cannot download release checksums."

	if [ -r /etc/os-release ]; then
		. /etc/os-release
	else
		error "Unsupported operating system (no /etc/os-release)."
	fi

    local kind selected
    if requires_appimage || [ "${ID:-}" = solus ]; then kind=appimage
    else
        case "${ID:-} ${ID_LIKE:-}" in
            *debian*|*ubuntu*|*deepin*) kind=deb ;;
            *suse*|*fedora*|*rhel*|*centos*|*rocky*|*almalinux*) kind=rpm ;;
            *arch*|*manjaro*|*biglinux*|*bigcommunity*|*cachyos*|*artix*) kind=arch ;;
            *) error "Unsupported operating system." ;;
        esac
    fi
    selected=$(python3 "$_architecture_cli" release --kind "$kind" "$_architecture_work/release.json") || error "No unique verified native LinuxToys release asset."
    case "$kind" in
        deb) _deb="$selected"; _deb_name=$(basename "$_deb") ;;
        rpm) _rpm="$selected"; _rpm_name=$(basename "$_rpm") ;;
        arch) _pkg="$selected"; _pkg_name=$(basename "$_pkg") ;;
        appimage) _appimage="$selected"; _appimage_name=$(basename "$_appimage") ;;
    esac

    # Select the AppImage before either the ostree check or ID_LIKE can route
    # an immutable host to a native package installation.
    if requires_appimage; then
        osappimage
        return "$?"
    fi

	case "${ID:-}" in
		debian|ubuntu|deepin) osdeb; return "$?" ;;
		fedora|rhel|centos|rocky|almalinux) osrpm; return "$?" ;;
		suse|opensuse) ossuse; return "$?" ;;
		manjaro|biglinux|bigcommunity) manjaro; return "$?" ;;
		steamos) osappimage; return "$?" ;;
		arch|cachyos|artix) osarch; return "$?" ;;
		solus) osappimage; return "$?" ;;
	esac

	case "${ID_LIKE:-}" in
		*debian*|*ubuntu*) osdeb; return "$?" ;;
		*rhel*|*fedora*) osrpm; return "$?" ;;
		*manjaro*) manjaro; return "$?" ;;
		*suse*) ossuse; return "$?" ;;
		*arch*)
			if [ "${ID:-}" = "steamos" ]; then
				osappimage
			else
				osarch
			fi
            return "$?"
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
