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

# Progress/warning printers that do not end the run (info exits by design).
# _lt-namespaced: install.sh is also sourced into the background updater's
# shell, where linuxtoys.bash already defines info/warn/error.
_lt_note() { printf "\e[0;36m[INFO]\e[m %s\n" "${1}"; }

_lt_warn() { printf "\e[0;33m[WARN]\e[m %s\n" "${1}"; }

# ---------------------------------------------------------------------------
# Native package-manager guard.
#
# install.sh drives the distribution's package manager directly, both as the
# one-shot installer and as the self-updater's payload (the app pipes this
# file into bash), so LinuxToys' own runtime guards — the package_guard
# preflight and libs/packages.bash's per-manager lock trios — are not around
# when it runs. The same postures are inlined here, mirroring packages.bash:
# a bounded wait for a running manager, stale-lock recovery for pacman (the
# only manager whose lock file outlives its process and blocks new
# transactions on existence alone), and transaction wrappers that stand by
# for a manager that starts between the guard and the call instead of
# surfacing an opaque lock failure.
# ---------------------------------------------------------------------------

LT_GUARD_TIMEOUT=300
LT_GUARD_TIMEOUT_MSG="Another package operation is still running and is taking too long. Please wait for the ongoing operation to finish, then try again."

# fd-link lines under /proc, elevated when a cached sudo ticket is already
# held (root-owned holders — pacman, pamac-daemon, packagekitd,
# unattended-upgr — are invisible to an unprivileged scan); with no ticket
# available the plain scan keeps the best-effort behavior, and the
# named-process checks in the busy checks below still catch those holders.
_lt_lock_fd_links () {
	if [ "$(id -u)" -eq 0 ]; then
		find /proc/[0-9]*/fd -maxdepth 1 -type l -printf '%l\n' 2>/dev/null || true
	elif sudo -n true >/dev/null 2>&1; then
		sudo -n find /proc/[0-9]*/fd -maxdepth 1 -type l -printf '%l\n' 2>/dev/null || true
	else
		find /proc/[0-9]*/fd -maxdepth 1 -type l -printf '%l\n' 2>/dev/null || true
	fi
}

# Whether the lock paths matching $1 are verifiably held open by a live
# process right now. A lock file merely existing is stale evidence (a crash
# leftover); this is the fd-link test packages.bash and
# package_guard._lock_actively_held use.
_lt_lock_held () {
	_lt_lock_fd_links | grep -Eq "$1"
}

_lt_pacman_lock_held () { _lt_lock_held '^/var/lib/pacman/db\.lck( \(deleted\))?$'; }
_lt_deb_lock_held () { _lt_lock_held '^(/var/lib/dpkg/lock(-frontend)?|/var/lib/apt/lists/lock|/var/cache/apt/archives/lock)( \(deleted\))?$'; }
_lt_dnf_lock_held () { _lt_lock_held '^(/var/lib/dnf/rpmdb\.lock|/run/dnf\.pid|/var/lib/dnf/lock)( \(deleted\))?$'; }
_lt_zypp_lock_held () { _lt_lock_held '^(/run/zypp\.pid|/var/run/zypp\.pid)( \(deleted\))?$'; }

# Name of a running manager of the family, else false. Transaction tools are
# proof of a transaction on their own; resident daemons (alive whenever a
# software centre or an auto-update timer is installed) only count while they
# plausibly hold the package lock.
_lt_arch_busy () {
	local _name
	for _name in pacman paru pamac yay; do
		if pgrep -x "$_name" >/dev/null 2>&1; then
			echo "$_name"
			return 0
		fi
	done
	if pgrep -x pamac-daemon >/dev/null 2>&1 && [ -e /var/lib/pacman/db.lck ]; then
		echo "pamac-daemon"
		return 0
	fi
	return 1
}

_lt_deb_busy () {
	local _name
	for _name in apt apt-get dpkg dpkg-deb pkcon; do
		if pgrep -x "$_name" >/dev/null 2>&1; then
			echo "$_name"
			return 0
		fi
	done
	for _name in unattended-upgr apt.systemd.dai packagekitd apt-key; do
		if pgrep -x "$_name" >/dev/null 2>&1 && _lt_deb_lock_held; then
			echo "$_name"
			return 0
		fi
	done
	return 1
}

_lt_dnf_busy () {
	local _name
	for _name in dnf dnf5 yum; do
		if pgrep -x "$_name" >/dev/null 2>&1; then
			echo "$_name"
			return 0
		fi
	done
	if pgrep -x dnf-automatic >/dev/null 2>&1 && _lt_dnf_lock_held; then
		echo "dnf-automatic"
		return 0
	fi
	return 1
}

_lt_zypp_busy () {
	if pgrep -x zypper >/dev/null 2>&1; then
		echo "zypper"
		return 0
	fi
	if pgrep -x zypp-refresh >/dev/null 2>&1 && _lt_zypp_lock_held; then
		echo "zypp-refresh"
		return 0
	fi
	return 1
}

# Bounded wait ($1 = busy-check function name) for the running manager to go
# idle. Returns 1 when a manager is still running after LT_GUARD_TIMEOUT.
_lt_busy_wait () {
	local _check="$1" _manager _waited=0
	if ! _manager=$("$_check"); then
		return 0
	fi
	_lt_warn "Another package operation (${_manager}) is in progress. Waiting for it to finish..."
	while _manager=$("$_check"); do
		if [ "$_waited" -ge "$LT_GUARD_TIMEOUT" ]; then
			return 1
		fi
		sleep 3
		_waited=$((_waited + 3))
	done
	return 0
}

# Bounded standby for a lock still held after the busy-wait (a live holder
# the manager list cannot name — an AUR helper or another libalpm/zypp
# client). Returns 1 when the holder outlasted LT_GUARD_TIMEOUT.
_lt_lock_standby () {
	local _check="$1" _waited=0
	while "$_check"; do
		if [ "$_waited" -ge "$LT_GUARD_TIMEOUT" ]; then
			return 1
		fi
		sleep 3
		_waited=$((_waited + 3))
	done
	return 0
}

# Stale-pacman-lock recovery: alpm refuses new transactions while db.lck
# exists even when nothing holds it, so a crash leftover must be removed
# rather than failing every call below until it is cleaned up by hand.
# Returns 1 when there is no leftover to recover.
_lt_stale_pacman_recovery () {
	[ -f /var/lib/pacman/db.lck ] || return 1
	# The caller waits out verifiably live holders before this runs, so a
	# lock file that still exists is a crash leftover, never a live hold.
	_lt_warn "Stale pacman lock detected. Removing /var/lib/pacman/db.lck"
	if ! sudo rm -f /var/lib/pacman/db.lck; then
		error "Failed to remove stale lock. Run: sudo rm /var/lib/pacman/db.lck"
	fi
}

# Run "$@" as one native package-manager transaction with the runners'
# guard+retry recovery (mirrors libs/packages.bash's *_transaction trios):
# wait out a manager that is already running, recover the family's
# crash-leftover lock where it has one (pacman), and on a lock-refused
# attempt stand by for the holder and re-run instead of surfacing an opaque
# lock failure.
#
# Contract:
#   0        transaction completed
#   nonzero  failed on its own; the caller's error path applies
#   exit 1   a holder outlasted the bounded waits (the timeout message)
_lt_transaction () {
	local _busy="$1" _lock="$2" _stale="$3"
	shift 3

	if ! _lt_busy_wait "$_busy"; then
		error "$LT_GUARD_TIMEOUT_MSG"
	fi
	if "$_lock"; then
		# A live holder the manager list cannot name: stand by for it before
		# the first attempt instead of costing that attempt a lock error.
		_lt_note "Another package operation is in progress. Waiting for it to finish..."
		if ! _lt_lock_standby "$_lock"; then
			error "$LT_GUARD_TIMEOUT_MSG"
		fi
	fi
	if [ -n "$_stale" ]; then
		"$_stale"
	fi
	while true; do
		local _status=0
		"$@" || _status=$?
		if [ "$_status" -eq 0 ]; then
			return 0
		fi
		if "$_lock" || "$_busy" >/dev/null 2>&1; then
			if ! _lt_busy_wait "$_busy"; then
				error "$LT_GUARD_TIMEOUT_MSG"
			fi
			if "$_lock"; then
				_lt_note "Another package operation is in progress. Waiting for it to finish..."
				if ! _lt_lock_standby "$_lock"; then
					error "$LT_GUARD_TIMEOUT_MSG"
				fi
			fi
			# The standby exits only once the lock is free; retry below.
		elif [ -n "$_stale" ] && "$_stale"; then
			# A crash leftover between the entry recovery and this call:
			# the same verified removal, not a live hold.
			:
		else
			# Not attributable to a lock: the caller's own error path applies,
			# with the same status a bare call would have produced.
			return "$_status"
		fi
	done
}

pacman_transaction () {
	_lt_transaction _lt_arch_busy _lt_pacman_lock_held _lt_stale_pacman_recovery "$@"
}

# The apt family keeps no stale branch: dpkg locks are fcntl-held and
# released when their holder dies.
apt_transaction () {
	_lt_transaction _lt_deb_busy _lt_deb_lock_held '' "$@"
}

# dnf, and yum on hosts without dnf.
dnf_transaction () {
	_lt_transaction _lt_dnf_busy _lt_dnf_lock_held '' "$@"
}

# YaST and KDE's update applet hold the zypp lock like any other client; the
# fd standby covers a holder the manager list cannot name.
zypper_transaction () {
	_lt_transaction _lt_zypp_busy _lt_zypp_lock_held '' "$@"
}

# ---------------------------------------------------------------------------
# Installed-state gate and repair.
#
# The handlers below drive the package manager with this release's asset,
# but a manager asked to install the very version it already has silently
# no-ops: apt reports "already the newest version", dnf/yum have nothing to
# do for a same-version local install, and pamac skips the build of an
# up-to-date package. A third-party package operation can then delete a
# package-owned file — another vendor's "legacy files cleanup" removed the
# LinuxToys desktop entry exactly this way (discussion #1500) — and a
# rerun of install.sh still ended in "LinuxToys installed or updated!"
# with the damage left in place.
#
# When the installed version already equals this release's tag, the gate
# below verifies the installation with the package manager's own integrity
# check instead: an intact installation exits as "already installed and up
# to date", and a damaged one is reinstalled with the handler's repair
# semantics (_lt_repair: apt --reinstall, dnf/yum reinstall, a removal
# before the pamac build). Older installations keep the plain update path;
# newer, foreign or undetectable installations keep the legacy behavior.
# LINUXTOYS_REINSTALL=1 forces the clean reinstall of an intact
# same-version installation.
# ---------------------------------------------------------------------------

# The installed Arch-family LinuxToys package as "name version" — the
# release package 'linuxtoys' or the AUR prebuilt 'linuxtoys-bin' — or
# rc 1 when neither is installed.
_lt_arch_installed () {
	local out
	out=$(pacman -Q linuxtoys 2>/dev/null) || true
	if [ -n "$out" ]; then
		printf '%s\n' "$out"
		return 0
	fi
	out=$(pacman -Q linuxtoys-bin 2>/dev/null) || true
	if [ -n "$out" ]; then
		printf '%s\n' "$out"
		return 0
	fi
	return 1
}

# AppImage paths referenced by installed LinuxToys desktop entries (user
# entries first). Gear Lever, the AppImage route's integrator, points the
# entry's Exec at the integrated file itself.
_lt_appimage_paths () {
	local dir entry exec_line
	for dir in "${HOME}/.local/share/applications" /usr/share/applications; do
		[ -d "$dir" ] || continue
		while IFS= read -r entry; do
			[ -n "$entry" ] || continue
			exec_line=$(grep -m1 -h '^Exec=' "$entry" 2>/dev/null) || true
			[ -n "$exec_line" ] || continue
			exec_line=${exec_line#Exec=}
			if [[ $exec_line == \"* ]]; then
				exec_line=${exec_line#\"}
				exec_line=${exec_line%%\"*}
			else
				exec_line=${exec_line%%[[:space:]]*}
			fi
			[ -n "$exec_line" ] || continue
			case "${exec_line,,}" in
				*linuxtoys*.appimage) printf '%s\n' "$exec_line" ;;
			esac
		done < <(grep -ils -- 'linuxtoys' "$dir"/*.desktop 2>/dev/null)
	done
	return 0
}

# The release version baked into the referenced AppImage file names
# (LinuxToys-<version>-<arch>.AppImage), or rc 1 when the entries reference
# no single parseable version.
_lt_appimage_version () {
	local path base version
	local -A seen=()
	local -a paths versions=()
	mapfile -t paths < <(_lt_appimage_paths)
	[ "${#paths[@]}" -gt 0 ] || return 1
	for path in "${paths[@]}"; do
		base=${path##*/}
		base=${base%.*}
		version=${base#*-}
		version=${version%-*}
		[[ $version =~ ^[0-9]+(\.[0-9]+)*$ ]] || continue
		if [ -n "${seen[$version]:-}" ]; then
			continue
		fi
		seen[$version]=1
		versions+=("$version")
	done
	[ "${#versions[@]}" -eq 1 ] || return 1
	printf '%s\n' "${versions[0]}"
	return 0
}

# Compare two versions as plain dotted numbers, right-padded with zeros.
# Prints -1|0|1 (first versus second) and returns 0; returns 1 when either
# side is not comparable, so the caller can fall back to the legacy path.
# Debian epochs/revisions and Arch release numbers are not the release
# version and are stripped first.
_lt_version_cmp () {
	local a b i x y
	a=${1-} a=${a#v} a=${a##*:} a=${a%%-*} a=${a%%~*}
	b=${2-} b=${b#v} b=${b##*:} b=${b%%-*} b=${b%%~*}
	[[ $a =~ ^[0-9]+(\.[0-9]+)*$ ]] || return 1
	[[ $b =~ ^[0-9]+(\.[0-9]+)*$ ]] || return 1
	local -a A=() B=()
	IFS=. read -r -a A <<< "$a"
	IFS=. read -r -a B <<< "$b"
	for ((i = 0; i < ${#A[@]} || i < ${#B[@]}; i++)); do
		x=${A[i]:-0}
		y=${B[i]:-0}
		if [ "$x" -lt "$y" ]; then
			printf '%s\n' -1
			return 0
		fi
		if [ "$x" -gt "$y" ]; then
			printf '%s\n' 1
			return 0
		fi
	done
	printf '%s\n' 0
	return 0
}

# Installed version of the LinuxToys package for the resolved route, or
# rc 1 when no installation this route manages can be detected (not
# installed, installed through another route, or no parseable version).
_lt_installed_version () {
	local out
	case "${_route_handler:-}" in
	osdeb)
		out=$(dpkg-query -W -f='${Version}\n' linuxtoys 2>/dev/null) || true
		;;
	osrpm|ossuse)
		out=$(rpm -q --qf '%{VERSION}\n' linuxtoys 2>/dev/null) || true
		;;
	osarch)
		out=$(_lt_arch_installed 2>/dev/null) || true
		out=${out##* }
		;;
	manjaro)
		out=$(pacman -Q linuxtoys-bin 2>/dev/null) || true
		out=${out##* }
		;;
	osappimage)
		out=$(_lt_appimage_version 2>/dev/null) || true
		;;
	*)
		return 1
		;;
	esac
	[ -n "$out" ] || return 1
	printf '%s\n' "$out"
	return 0
}

# Whether the installed LinuxToys package of the resolved route is damaged:
# package-owned files missing or altered. Prints nothing; returns 0 when
# damaged, 1 when intact or unverifiable. The callers run it only after
# _lt_installed_version proved the package present.
_lt_install_damaged () {
	local out rc flags pkg path
	case "${_route_handler:-}" in
	osdeb)
		# Every file the package owns must still exist.
		while IFS= read -r pkg; do
			if [ -n "$pkg" ] && [ ! -e "$pkg" ]; then
				return 0
			fi
		done < <(dpkg-query -L linuxtoys 2>/dev/null)
		# dpkg's own md5 verification for altered files; rc 1 means the
		# verification failed, while older dpkg builds without --verify
		# (rc 2 or a missing binary) leave the existence scan above alone.
		rc=0
		dpkg --verify linuxtoys >/dev/null 2>&1 || rc=$?
		if [ "$rc" -eq 1 ]; then
			return 0
		fi
		return 1
		;;
	osrpm|ossuse)
		# rpm reports benign metadata drift (mtime, user, group) the same
		# way as real damage; only presence, content, size, mode and
		# symlink failures count. LC_ALL=C keeps the report format
		# parseable everywhere.
		out=$(LC_ALL=C rpm -V linuxtoys 2>/dev/null)
		rc=$?
		if [ "$rc" -eq 0 ]; then
			return 1
		fi
		while IFS= read -r flags; do
			if [ -z "$flags" ]; then
				continue
			fi
			flags=${flags%%[[:space:]]*}
			# rpm -V flags: size, mode, md5, device, symlink at fixed
			# positions; "missing" (or the all-unknown mask) means the
			# file is gone.
			case "$flags" in
				S*|?M*|??5*|???D*|????L*|'?????'*|missing*) return 0 ;;
			esac
		done <<< "$out"
		return 1
		;;
	osarch)
		out=$(_lt_arch_installed 2>/dev/null) || return 1
		pkg=${out%% *}
		;;
	manjaro)
		pkg=linuxtoys-bin
		;;
	osappimage)
		mapfile -t path < <(_lt_appimage_paths)
		if [ "${#path[@]}" -eq 0 ]; then
			return 0
		fi
		for pkg in "${path[@]}"; do
			if [ ! -f "$pkg" ] || [ ! -x "$pkg" ] || [ ! -s "$pkg" ]; then
				return 0
			fi
		done
		return 1
		;;
	*)
		return 1
		;;
	esac
	# pacman's -kk check reports missing files and directory permission
	# damage; a clean run is silent and exits 0. LC_ALL=C keeps the report
	# format parseable for the output check.
	out=$(LC_ALL=C pacman -Qkk "$pkg" 2>&1)
	rc=$?
	if [ "$rc" -ne 0 ]; then
		return 0
	fi
	if printf '%s\n' "$out" | grep -Eq 'missing|No such file|incorrect permission'; then
		return 0
	fi
	return 1
}

# The installed-state gate for the resolved route. Sets _lt_repair when the
# handlers must use repair/reinstall semantics, and terminates the run via
# info() when an intact installation is already at this release's version.
_lt_repair_gate () {
	local installed cmp tag forced
	_lt_repair=""
	forced=0
	if [ "${LINUXTOYS_REINSTALL:-0}" = "1" ]; then
		forced=1
	fi
	installed=$(_lt_installed_version) || return 0
	if [ -z "$installed" ]; then
		return 0
	fi
	tag=${_tag_name-}
	tag=${tag#v}
	cmp=$(_lt_version_cmp "$installed" "$tag") || return 0
	if [ "$cmp" -ne 0 ]; then
		# Older: the plain update path below. Newer: the legacy behavior —
		# the release asset would be a downgrade, which is the manager's
		# call, exactly as before this gate existed.
		return 0
	fi
	if [ "$forced" -eq 0 ]; then
		if _lt_install_damaged; then
			_lt_warn "LinuxToys ${_tag_name} is installed but damaged (missing or altered files). Reinstalling to repair it..."
		else
			info "LinuxToys ${_tag_name} is already installed and up to date. Nothing to do (set LINUXTOYS_REINSTALL=1 to force a clean reinstall)."
		fi
	else
		_lt_note "Forcing a clean reinstall of LinuxToys ${_tag_name}..."
	fi
	_lt_repair=1
	return 0
}

# Delegate ISA policy to the application; the installer never keeps its own
# alias tables. Stage the release's own read-only validation code, gate the
# host, and payload-verify every downloaded release artifact.
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
for path in paths:
    metadata = path.lstat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o022 or stat.S_ISLNK(metadata.st_mode):
        raise SystemExit(1)
PYLOCAL
    then
        _architecture_cli="$source_dir/p3/app/architecture_cli.py"
    else
        revision=$(python3 -c 'import json,sys; from urllib.parse import quote; print(quote(json.load(sys.stdin)["tag_name"], safe=""))' <<< "$_api") || error "Release has no source tag."
        revision=$(curl -fsSL "https://api.github.com/repos/psygreg/linuxtoys/commits/$revision" | python3 -c 'import json,re,sys; s=json.load(sys.stdin)["sha"]; assert re.fullmatch("[0-9a-f]{40}",s); print(s)') || error "Cannot resolve immutable release source."
        mkdir -p "$_architecture_work/app" || error "Cannot stage architecture helper."
        : > "$_architecture_work/app/__init__.py"
        for file in architecture.py architecture_files.py architecture_flatpak.py architecture_cli.py; do
            curl -fsSL "https://raw.githubusercontent.com/psygreg/linuxtoys/$revision/p3/app/$file" -o "$_architecture_work/app/$file" || error "Release lacks architecture validation; use a qualified release."
        done
        _architecture_cli="$_architecture_work/app/architecture_cli.py"
    fi
    python3 "$_architecture_cli" label host >/dev/null || error "Unsupported host architecture."
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

osdeb() {
	if curl -fsSL "${_deb}" -o "/tmp/${_deb_name}"; then
		architecture_verify "/tmp/${_deb_name}"
		apt_transaction sudo apt update || true
		if apt_transaction sudo apt install -y ${_lt_repair:+"--reinstall"} "/tmp/${_deb_name}"; then
			info "LinuxToys installed or updated!"
		else
			error "Installation failed (apt)."
		fi
	else
		error "Failed to download: ${_deb_name}"
	fi
}

osrpm() {
	local _dnf_verb
	if curl -fsSL "${_rpm}" -o "/tmp/${_rpm_name}"; then
		architecture_verify "/tmp/${_rpm_name}"
		_dnf_verb=install
		if [ -n "${_lt_repair:-}" ]; then
			_dnf_verb=reinstall
		fi
		if command -v dnf >/dev/null 2>&1; then
			{ [ "$ID" = "rhel" ]; } && sudo subscription-manager repos --enable codeready-builder-for-rhel-$(rpm -E %rhel)-$(arch)-rpms && dnf_transaction sudo dnf install https://dl.fedoraproject.org/pub/epel/epel-release-latest-$(rpm -E %rhel).noarch.rpm
			{ [[ "$ID_LIKE" = *rhel* ]] && [ "$ID" != "rhel" ]; } && sudo dnf config-manager --set-enabled crb && dnf_transaction sudo dnf install epel-release
			if dnf_transaction sudo dnf "$_dnf_verb" -y "/tmp/${_rpm_name}"; then
				info "LinuxToys installed or updated!"
			else
				error "Installation failed (dnf)."
			fi
		else
			if dnf_transaction sudo yum "$_dnf_verb" -y "/tmp/${_rpm_name}"; then
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
        architecture_verify "/tmp/${_rpm_name}"
        if sudo rpm -U --nodeps --replacefiles --replacepkgs "/tmp/${_rpm_name}"; then
            dependencies=(
                bash git curl wget zenity python3 python3-gobject gtk3
                python3-requests python3-urllib3 python3-certifi util-linux
                libvte-2_91-0 typelib-1_0-Vte-2.91 libappstream5 typelib-1_0-AppStream-1.0
                AppStream adwaita-icon-theme libzypp-plugin-appdata
            )
            for pkg in "${dependencies[@]}"; do
                zypper_transaction sudo zypper --non-interactive install "${pkg}"
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
    [ -n "${_pkg:-}" ] || error "No Arch Linux package was found in the latest LinuxToys release."
    [ -n "${_pkg_name:-}" ] || error "Could not determine the LinuxToys Arch package filename."

    if pacman -Qi linuxtoys-bin &>/dev/null; then
        pacman_transaction sudo pacman -R --noconfirm linuxtoys-bin ||
            error "Failed to remove existing linuxtoys-bin package."
    fi

    if curl -fL --retry 3 "${_pkg}" -o "/tmp/${_pkg_name}"; then
        architecture_verify "/tmp/${_pkg_name}"
        if [ "$ID" = "cachyos" ]; then
            dependencies=(
                bash git curl wget zenity appstream archlinux-appstream-data
                python python-gobject python-requests gtk3 vte3 sudo util-linux
                webp-pixbuf-loader
            )
            for pkg in "${dependencies[@]}"; do
                pacman_transaction sudo pacman -S --noconfirm --needed "${pkg}"
            done
        fi
        if pacman_transaction sudo pacman -U --noconfirm "/tmp/${_pkg_name}"; then
            info "LinuxToys installed or updated!"
        else
            error "Installation failed (pacman)."
        fi
    else
        error "Failed to download: ${_pkg_name}"
    fi
}

osappimage() {
	local _appimage_dir _appimage_file _flatpak_scope _output

	[ -n "${_appimage:-}" ] || error "No AppImage was found in the latest LinuxToys release."
	[ -n "${_appimage_name:-}" ] || error "Could not determine the LinuxToys AppImage filename."

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

	_appimage_dir=$(mktemp -d "${TMPDIR:-/tmp}/linuxtoys-appimage.XXXXXX") ||
		error "Failed to create temporary AppImage directory."
	trap 'rm -rf -- "${_appimage_dir}"' EXIT
	_appimage_file="${_appimage_dir}/${_appimage_name}"

	printf "\e[0;36m[INFO]\e[m Downloading LinuxToys AppImage...\n"
	curl -fL --retry 3 "${_appimage}" -o "${_appimage_file}" ||
		error "Failed to download: ${_appimage_name}"
	architecture_verify "${_appimage_file}"
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

manjaro() {
    if [ -n "${_lt_repair:-}" ]; then
        # pamac skips the build of an up-to-date package, so a same-version
        # repair must remove the damaged package first; the AUR build then
        # installs a fresh copy.
        if pacman -Qi linuxtoys-bin &>/dev/null; then
            pacman_transaction sudo pacman -R --noconfirm linuxtoys-bin ||
                error "Failed to remove the damaged linuxtoys-bin package."
        fi
    fi
    { pacman_transaction sudo pamac build linuxtoys-bin && info "LinuxToys installed or updated!"; } || error "Failed to build linuxtoys-bin from the AUR."
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

# Resolve the installation route for this host: which handler runs and which
# release-asset kind that handler consumes (empty when the handler needs no
# package asset at all — the Manjaro-family AUR build). $ID wins; $ID_LIKE is
# only the fallback when no known ID matches, mirroring os-release semantics.
# Immutable hosts and Solus always take the AppImage route.
_resolve_route() {
    if requires_appimage || [ "${ID:-}" = solus ]; then
        _route_handler=osappimage
        _route_kind=appimage
        return 0
    fi
    case "${ID:-}" in
        debian|ubuntu|deepin) _route_handler=osdeb; _route_kind=deb ;;
        fedora|rhel|centos|rocky|almalinux) _route_handler=osrpm; _route_kind=rpm ;;
        suse|opensuse) _route_handler=ossuse; _route_kind=rpm ;;
        manjaro|biglinux|bigcommunity) _route_handler=manjaro; _route_kind="" ;;
        steamos) _route_handler=osappimage; _route_kind=appimage ;;
        arch|cachyos|artix) _route_handler=osarch; _route_kind=arch ;;
        *)
            case "${ID_LIKE:-}" in
                *debian*|*ubuntu*) _route_handler=osdeb; _route_kind=deb ;;
                *rhel*|*fedora*) _route_handler=osrpm; _route_kind=rpm ;;
                *manjaro*) _route_handler=manjaro; _route_kind="" ;;
                *suse*) _route_handler=ossuse; _route_kind=rpm ;;
                *arch*) _route_handler=osarch; _route_kind=arch ;;
                *) return 1 ;;
            esac
            ;;
    esac
}

installer() {
	printf "\e[0;36m[INFO]\e[m Fetching latest release from GitHub...\n"
	_api=$(curl -fsSL "https://api.github.com/repos/psygreg/linuxtoys/releases/latest" 2>/dev/null)

	if [ -z "${_api}" ]; then
		printf "\e[0;33m[WARN]\e[m GitHub unavailable, trying Gitea server at git.linux.toys...\n"
		_api=$(curl -fsSL "https://git.linux.toys/api/v1/repos/psygreg/linuxtoys/releases/latest" 2>/dev/null)
	fi

	if [ -z "${_api}" ]; then
		error "Failed to fetch release information from GitHub and git.linux.toys"
	fi

	_tag_name=$(echo "${_api}" | grep -Pio '"tag_name":\s*"\K[^"]+')

	if [ -r /etc/os-release ]; then
		. /etc/os-release
	else
		error "Unsupported operating system (no /etc/os-release)."
	fi

	# Resolve the route, then the installed state: an installation already
	# at this release's version is verified and repaired instead of
	# blind-reinstalled (a same-version reinstall would silently keep any
	# damage), and an intact one needs neither the architecture staging nor
	# any download at all.
	_route_handler="" _route_kind=""
	_resolve_route || error "Unsupported operating system."
	_lt_repair=""
	_lt_repair_gate

	# Stage the release's own architecture validation, verify the host, and
	# select exactly one verified native release asset with its checksum
	# manifest (no positional/foreign fallback).
	architecture_prepare
	_checksum_url=$(python3 -c 'import json,sys; a=[x["browser_download_url"] for x in json.load(sys.stdin).get("assets",[]) if x.get("name")=="sha256sums.txt"]; assert len(a)==1 and a[0].startswith("https://"); print(a[0])' <<< "$_api") || error "Release has no unique checksum manifest."
	curl -fsSL "$_checksum_url" -o "$_architecture_work/sha256sums.txt" || error "Cannot download release checksums."

	# Select only the release asset that route consumes. The staged ISA
	# policy (architecture_prepare/verify) refuses foreign or unreviewed
	# payloads, so a host whose architecture has no native package of its
	# kind in the release — an aarch64 host on an x86-only release — has no
	# candidate at all here.
	local selected _kind_label
	if [ -n "${_route_kind}" ]; then
		if selected=$(python3 "$_architecture_cli" release --kind "${_route_kind}" "$_architecture_work/release.json"); then
			case "${_route_kind}" in
				deb) _deb="$selected"; _deb_name=$(basename "$_deb") ;;
				rpm) _rpm="$selected"; _rpm_name=$(basename "$_rpm") ;;
				arch) _pkg="$selected"; _pkg_name=$(basename "$_pkg") ;;
				appimage) _appimage="$selected"; _appimage_name=$(basename "$_appimage") ;;
			esac
		# Availability fallback: the AppImage route itself has nothing to fall
		# back to, but a native-package route may still find a verified native
		# AppImage for this host. Route through Gear Lever instead of failing
		# closed; the notice is the only thing separating this path from an
		# immutable-host installation.
		elif [ "${_route_kind}" != "appimage" ] &&
			_appimage=$(python3 "$_architecture_cli" release --kind appimage "$_architecture_work/release.json"); then
			_appimage_name=$(basename "$_appimage")
			case "${_route_kind}" in
				deb) _kind_label="Debian" ;;
				rpm) _kind_label="RPM" ;;
				arch) _kind_label="Arch Linux" ;;
			esac
			if [ -n "${_lt_repair:-}" ]; then
				# An AppImage cannot restore the native installation's files;
				# repairing through it would add a second install instead.
				error "Cannot repair the native LinuxToys installation: this release has no ${_kind_label} package for this architecture."
			fi
			_lt_warn "No native ${_kind_label} package for this architecture was found in the latest release. Falling back to the AppImage installation."
			osappimage
			return
		else
			error "No unique verified native LinuxToys release asset."
		fi
	fi

	"$_route_handler"
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
