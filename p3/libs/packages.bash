# --- Package Management ---

# Guards against pacman and apt database locks
pacman_lock_guard () {
    local PACMAN_ACTIVE=false
    if [ -f /var/lib/pacman/db.lck ]; then
        if pgrep -x pacman >/dev/null 2>&1; then
            PACMAN_ACTIVE=true
        elif command -v lsof >/dev/null 2>&1 && lsof /var/lib/pacman/db.lck >/dev/null 2>&1; then
            PACMAN_ACTIVE=true
        fi
        if [ "$PACMAN_ACTIVE" = true ]; then
            die "Another package operation is in progress (pacman is running). Please wait for it to finish, or close it manually and retry."
        else
            warn "Stale pacman lock detected. Removing /var/lib/pacman/db.lck"
            { { [ "$UPD_SERVICE" = "1" ] && rm -f /var/lib/pacman/db.lck; } || sudo rm -f /var/lib/pacman/db.lck; } || die "Failed to remove stale lock. Run: sudo rm /var/lib/pacman/db.lck"
        fi
    fi
}
interrupted_apt_guard () {
    if [ -n "$(dpkg --audit 2>/dev/null)" ]; then
        info "An interrupted package operation was detected. Attempting recovery..."
        { { [ "$UPD_SERVICE" = "1" ] && dpkg --configure -a; } || sudo dpkg --configure -a; } || die "Failed to recover interrupted dpkg operation. Manual user intervention required."
        { { [ "$UPD_SERVICE" = "1" ] && apt --fix-broken install -y; } || sudo apt --fix-broken install -y; } || die "Failed to fix broken packages. Manual user intervention required."
    fi
}

pkg_exists () {
    pkg_found=()
    pkg_notfound=()
    
    for pak in "$@"; do
        if is_debian || is_ubuntu; then
            if dpkg -s "$pak" &>/dev/null; then
                pkg_found+=("$pak")
            else
                pkg_notfound+=("$pak")
            fi
        elif is_arch || is_cachy || is_manjaro; then
            if pacman -Qi "$pak" &>/dev/null; then
                pkg_found+=("$pak")
            else
                pkg_notfound+=("$pak")
            fi
        elif is_fedora || is_ostree || is_suse || is_rhel; then
            if rpm -qi "$pak" &>/dev/null; then
                pkg_found+=("$pak")
            else
                pkg_notfound+=("$pak")
            fi
        elif is_solus; then     
            if eopkg list-installed | grep -qw "$pak"; then
                pkg_found+=("$pak")
            else
                pkg_notfound+=("$pak")
            fi
        fi
    done
}

pkg_install () {
    # Handle --ignore-appends and --ostreecheck flags
    local _ignore_appends=0
    local _ostreecheck=0
    local _allowerasing=0
    local -a _filtered_args=()
    for arg in "$@"; do
        if [[ "$arg" == "--ignore-appends" ]]; then
            _ignore_appends=1
        elif [[ "$arg" == "--ostreecheck" ]]; then
            _ostreecheck=1
        elif [[ "$arg" == "--allowerasing" ]]; then
            _allowerasing=1
        else
            _filtered_args+=("$arg")
        fi
    done
    
    pkg_exists "${_filtered_args[@]}"
    [[ ${#pkg_notfound[@]} -eq 0 ]] && return 0
    local to_install="${pkg_notfound[*]}"
    if is_debian || is_ubuntu; then
        interrupted_apt_guard
        sudo apt-get install -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    elif is_arch || is_cachy || is_manjaro; then
        if ! is_manjaro; then
            if ! pacman-conf --repo-list 2>/dev/null | grep -qx 'extra'; then 
                prep_edit /etc/pacman.conf
                printf '\n[extra]\nInclude = /etc/pacman.d/mirrorlist\n' |
                    sudo tee -a /etc/pacman.conf >/dev/null
            fi
        fi
        local _pacman_pkgs=()
        local _paru_pkgs=()
        for pak in "${pkg_notfound[@]}"; do
            # Use an exact sync-db lookup so AUR-only packages are not misclassified.
            if pacman -Si "$pak" &>/dev/null; then
                _pacman_pkgs+=("$pak")
            else
                _paru_pkgs+=("$pak")
            fi
        done
        local to_install_pacman="${_pacman_pkgs[*]}"
        local to_install_paru="${_paru_pkgs[*]}"
        # check for lock before installing
        if [ -n "$to_install_pacman" ]; then
            if is_manjaro; then
                pamac install --no-confirm "${_pacman_pkgs[@]}" || fatal "Failed to install $to_install_pacman"
                [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install_pacman"
            else
                pacman_lock_guard
                sudo pacman -S --noconfirm "${_pacman_pkgs[@]}" || fatal "Failed to install $to_install_pacman"
                [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install_pacman"
            fi
        fi
        if [ -n "$to_install_paru" ]; then
            if is_manjaro; then
                pamac build --no-confirm "${_paru_pkgs[@]}" || die "Failed to install $to_install_paru"
            else
                if ! command -v paru &>/dev/null; then
                    if question "Installer" "$msg305" 300 300; then
                        if pacman -Si paru &>/dev/null; then
                            pkg_install paru || fatal "Failed to install paru"
                        else
                            call_script paru
                        fi
                    else
                        die "User cancelled installation of paru"
                    fi
                fi
                if ! paru --version >/dev/null 2>&1; then # handle broken paru compiled against different libs, fix #1196
                    call_script paru
                fi
                paru -S -a --noconfirm --skipreview "${_paru_pkgs[@]}" || die "Failed to install $to_install_paru"
                [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install_paru"
            fi
        fi
    elif is_ostree; then
        sudo rpm-ostree install "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
        # Perform ostree check if requested and packages were actually installed
        if [[ $_ostreecheck -eq 1 && ${#pkg_notfound[@]} -gt 0 ]]; then
            zenwrn "$msgostreepending"
            exit 100
        fi
    elif is_fedora || is_rhel; then
        if [[ $_allowerasing -eq 1 ]]; then
            sudo dnf install -y --allowerasing "${pkg_notfound[@]}" || die "Failed to install $to_install"
        else
            sudo dnf install -y "${pkg_notfound[@]}" || die "Failed to install $to_install"
        fi
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    elif is_suse; then
        sudo zypper in -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    elif is_solus; then
        sudo eopkg it -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    fi
}

pkg_flat() {
    local _skip_user=0
    local -a _flatpak_args=()
    for arg in "$@"; do
        if [[ "$arg" == "--skip-user" ]]; then
            _skip_user=1
        else
            _flatpak_args+=("$arg")
        fi
    done
    if ! command -v flatpak &>/dev/null || ! flatpak remote-list | grep -q flathub; then
        call_script flathub
    fi
    local flatpak_scope="--user"
    if [[ $_skip_user -eq 1 ]]; then
        flatpak_scope="--system"
    elif flatpak remote-list --system 2>/dev/null | grep -q flathub && \
       ! flatpak remote-list --user 2>/dev/null | grep -q flathub; then
        flatpak_scope="--system"
    fi

    # Extract base package names (remove version/architecture specifications)
    local -a _flatpak_basenames=()
    for arg in "${_flatpak_args[@]}"; do
        local basename="${arg%%/*}"
        _flatpak_basenames+=("$basename")

        # Only mark applications that weren't already installed
        if ! flatpak info "$flatpak_scope" "$arg" &>/dev/null; then
            _flatpak_new+=("$arg")
        fi
    done

    if [ "$flatpak_scope" = "--user" ]; then
        flatpak install --or-update "$flatpak_scope" -y flathub "${_flatpak_args[@]}" || fatal "Failed to install flatpak packages ${_flatpak_args[*]}"
        for basename in "${_flatpak_basenames[@]}"; do
            flatpak list "$flatpak_scope" | grep -q "$basename" || fatal "Failed to install flatpak package $basename"
        done
    else
        flatpak install --or-update "$flatpak_scope" -y flathub "${_flatpak_args[@]}" 2>/dev/null || { sudo_rq && sudo flatpak install --or-update "$flatpak_scope" -y flathub "${_flatpak_args[@]}"; } 
        for basename in "${_flatpak_basenames[@]}"; do
            flatpak list "$flatpak_scope" | grep -q "$basename" || fatal "Failed to install flatpak package $basename"
        done
    fi
    if [[ ${#_flatpak_new[@]} -gt 0 ]]; then
        _append_transmap "flatpak ${_flatpak_new[*]}"
    fi
}

pkg_fromfile () {
    # Handle --ostreecheck flag
    local _ostreecheck=0
    local -a _filtered_args=()
    for arg in "$@"; do
        if [[ "$arg" == "--ostreecheck" ]]; then
            _ostreecheck=1
        else
            _filtered_args+=("$arg")
        fi
    done
    
    # Use filtered args for the rest of the function
    set -- "${_filtered_args[@]}"
    
    if [[ "$1" == *.flatpak ]]; then
        if ! which flatpak &>/dev/null || ! flatpak remote-list | grep -q flathub; then
            summon_helpers
            sudo_rq
            flatpak_in_lib
        fi
        local flatpak_file="$1"
        local flatpak_scope="--user"
        if flatpak remote-list --system 2>/dev/null | grep -q flathub && \
           ! flatpak remote-list --user 2>/dev/null | grep -q flathub; then
            flatpak_scope="--system"
        fi
        local _flatpak_stderr
        if ! flatpak install "$flatpak_scope" --noninteractive "$flatpak_file" &>/dev/null; then  # force --system install
            _flatpak_stderr=$(
                sudo flatpak install --system --noninteractive "$flatpak_file" 2>&1 >/dev/null
            ) || fatal "Failed to install flatpak from file: $flatpak_file due to: $_flatpak_stderr"
        fi
        _append_transmap "pkg file $flatpak_file"
        return 0
    fi
    
    if is_debian || is_ubuntu; then
        { sudo apt-get -o APT::Sandbox::User=root install -y "${@}" || sudo dpkg -i "${@}"; } || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    elif { is_arch || is_cachy; } && ! is_manjaro; then
        # check for lock before installing local package
        pacman_lock_guard
        if sudo pacman -U "${@}"; then
            _append_transmap "pkg file $*"
        else
            if [ -f PKGBUILD ]; then
                local pkgname=$(grep "^pkgname=" PKGBUILD | head -1 | cut -d'=' -f2 | tr -d "'" '"')
                makepkg -si || fatal "Failed to build and install package $pkgname"
                _append_transmap "pkg file $pkgname"
            else
                fatal "Failed to install package $*"
            fi
        fi
    elif is_manjaro; then
        { pamac install --no-confirm "./${*}" && _append_transmap "pkg file $*"; } || fatal "Failed to install package $*"
    elif is_ostree; then
        sudo rpm-ostree install "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
        # Perform ostree check if requested
        if [[ $_ostreecheck -eq 1 ]]; then
            zenwrn "$msgostreepending"
            exit 100
        fi
    elif is_fedora || is_rhel; then
        sudo dnf install -y "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    elif is_suse; then
        sudo zypper in -y "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    elif is_solus; then
        sudo eopkg it -y "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    fi
}

pkg_fromurl () {
    [[ $# -gt 0 ]] || die "No package URLs provided"

    local url filename download_dir package_file
    local -a package_files=()
    prep_tmp_noram
    download_dir=$(mktemp -d ./pkg_fromurl.XXXXXX) || {
        die "Failed to create package download directory"
    }

    for url in "$@"; do
        filename="${url%%[?#]*}"
        filename="${filename##*/}"
        case "$filename" in
            ''|.|..)
                die "Package URL has no valid filename: $url"
                ;;
        esac
        package_file="$download_dir/${#package_files[@]}-$filename"
        curl -fL --retry 3 --output "$package_file" -- "$url" || {
            rm -f -- "$package_file"
            die "Failed to download package: $url"
        }
        package_files+=("$package_file")
    done

    for package_file in "${package_files[@]}"; do
        case "${package_file,,}" in
            *.appimage)
                pkg_appimage "$package_file"
                ;;
            *)
                pkg_fromfile "$package_file"
                ;;
        esac
    done
}

pkg_fromrelease () {
    [[ $# -ge 1 && $# -le 2 ]] || die "Usage: pkg_fromrelease REPOSITORY_URL [ASSET_GLOB]"
    local native_type="" package_url
    if is_arch || is_cachy; then
        native_type=arch
    elif is_fedora || is_rhel || is_ostree; then
        native_type=rpm
    elif is_debian || is_ubuntu; then
        native_type=deb
    elif is_solus; then
        native_type=eopkg
    fi

    package_url=$(python3 - "$1" "${2:-*}" "$native_type" "$(uname -m)" <<'PY'
import fnmatch
import json
import re
import subprocess
import sys
from urllib.parse import urlsplit


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


repository, pattern, native, machine = sys.argv[1:]
match = re.fullmatch(r"https://(github\.com|codeberg\.org)/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/?", repository)
if not match:
    fail("Expected https://github.com/OWNER/REPO or https://codeberg.org/OWNER/REPO")
host, owner, repo = match.groups()
repo = repo.removesuffix(".git")
if not repo or owner in (".", "..") or repo in (".", ".."):
    fail("Invalid repository name")
base = "https://api.github.com" if host == "github.com" else "https://codeberg.org/api/v1"
api = f"{base}/repos/{owner}/{repo}/releases/latest"
try:
    response = subprocess.run(
        ["curl", "-fsSL", "--retry", "3", "--connect-timeout", "15",
         "--max-time", "60", "-H", "Accept: application/json", "--", api],
        check=True, capture_output=True, text=True,
    )
    release = json.loads(response.stdout)
except (OSError, subprocess.CalledProcessError, ValueError) as error:
    fail(f"Failed to fetch latest release from {repository}: {error}")
if not isinstance(release, dict) or not isinstance(release.get("assets"), list):
    fail("Release API returned no asset list")
if release.get("draft") or release.get("prerelease"):
    fail("Latest release is not a stable published release")

aliases = {
    "x86_64": ("x86_64", "amd64", "x64"),
    "aarch64": ("aarch64", "arm64"),
    "i686": ("i386", "i486", "i586", "i686", "ia32", "x86"),
    "armv7l": ("armv7l", "armv7", "armhf"),
    "armv6l": ("armv6l", "armv6", "armel"),
    "riscv64": ("riscv64",),
    "ppc64le": ("ppc64le", "ppc64el"),
    "ppc64": ("ppc64",),
    "s390x": ("s390x",),
    "loongarch64": ("loongarch64",),
}
architecture = next((key for key, values in aliases.items() if machine in values), None)
if architecture is None:
    fail(f"Unsupported architecture: {machine}")
# Match longer aliases first so x86_64 is not mistaken for x86.
labels = sorted((label for values in aliases.values() for label in values), key=len, reverse=True)
arch_re = re.compile(r"(?<![a-z0-9])(" + "|".join(map(re.escape, labels)) + r")(?![a-z0-9])")
native_extensions = {"arch": (".pacman", ".pkg.tar.zst"), "rpm": (".rpm",),
                     "deb": (".deb",), "eopkg": (".eopkg",)}
formats = [(".appimage",), (".flatpak",), native_extensions.get(native, ())]
candidates = []
for asset in release["assets"]:
    name, url = asset.get("name", ""), asset.get("browser_download_url", "")
    if not isinstance(name, str) or not isinstance(url, str):
        continue
    lower = name.lower()
    if not fnmatch.fnmatchcase(lower, pattern.lower()) or urlsplit(url).scheme != "https":
        continue
    if re.search(r"(?:^|[._-])(?:debug|debuginfo|debugsource|devel|source|src)(?:[._-]|$)", lower):
        continue
    kind = next((i for i, extensions in enumerate(formats) if lower.endswith(extensions)), None)
    if kind is None:
        continue
    detected = set(arch_re.findall(lower))
    x86_fallback = False
    if detected and not detected.intersection(aliases[architecture]):
        if architecture == "x86_64" and detected.intersection(aliases["i686"]):
            x86_fallback = True
        else:
            continue
    # Use 32-bit x86 only when no native or architecture-unlabelled asset matches.
    # Within each tier, retain AppImage > Flatpak > native package preference.
    # Explicit architecture matches outrank assets whose names omit architecture.
    candidates.append(((x86_fallback, kind, 0 if detected else 1), name, url))
if not candidates:
    fail(f"No compatible release package for {machine} ({native or 'portable only'})")
best_rank = min(item[0] for item in candidates)
best = [item for item in candidates if item[0] == best_rank]
if len(best) != 1:
    fail("Multiple matching packages; pass an ASSET_GLOB to choose one:\n" +
         "\n".join(item[1] for item in best))
print(f"Selected {best[0][1]} from {release.get('tag_name', 'latest release')}", file=sys.stderr)
print(best[0][2])
PY
    ) || die "Failed to select a release package"

    pkg_fromurl "$package_url"
}

pkg_remove () {
    pkg_exists "$@"
    [[ ${#pkg_found[@]} -eq 0 ]] && return 0
    
    local to_remove="${pkg_found[*]}"
    
    if is_debian || is_ubuntu; then
        sudo apt-get remove -y --allow-unauthenticated "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif { is_arch || is_cachy; } && ! is_manjaro; then
        # check for lock before removing (stale lock otherwise aborts pacman -Rsn)
        pacman_lock_guard
        sudo pacman -Rsn --noconfirm "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_manjaro; then
        pamac remove --no-confirm "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_ostree; then
        sudo rpm-ostree uninstall "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_fedora || is_rhel ; then
        sudo dnf remove -y "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_suse; then
        sudo zypper rm -y "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    elif is_solus; then
        sudo eopkg rmf -y "${pkg_found[@]}" || fatal "Failed to remove packages: $to_remove"
    fi
    _append_transmap "pkg rm $to_remove"
}
pkg_rm () { pkg_remove "$@"; }

_pkg_appimage_previous () {
    python3 - "${LINUXTOYS_SCRIPT_NAME:-}" <<'PY'
import os
import sys
from pathlib import Path

name = sys.argv[1]
registry = Path.home() / ".cache/linuxtoys/registry"
if not name or not registry.exists():
    sys.exit(0)
try:
    content = registry.read_text()
    for entry in reversed(content.split("---\n")):
        lines = entry.strip().splitlines()
        if not lines or "Script: " not in lines[0]:
            continue
        if lines[0].split("Script: ", 1)[1].strip() != name:
            continue
        installed = set()
        for line in lines[1:]:
            operation = line.strip()
            if not operation.startswith("- appimage "):
                continue
            filename = operation[len("- appimage "):]
            if filename.startswith("rm "):
                continue
            # The installation logger records one complete basename per line.
            if filename in (".", "..") or "/" in filename or "\x00" in filename:
                raise ValueError("Invalid AppImage filename in registry")
            path = Path.home() / "AppImages" / filename
            if path.is_symlink():
                raise ValueError("Refusing to replace a symlinked AppImage")
            if path.is_file():
                installed.add(filename)
        if len(installed) > 1:
            raise ValueError("Multiple installed AppImages in this script's record; cannot choose an update target")
        if installed:
            print(installed.pop())
        break
except (OSError, ValueError) as error:
    print(f"Cannot resolve previous AppImage: {error}", file=sys.stderr)
    sys.exit(1)
PY
}

pkg_appimage () {
    [[ $# -gt 0 ]] || die "No AppImage files provided"
    # update handling
    local appimage_input previous_appimage
    local -a appimage_inputs=()
    # Integration helpers may change directories; resolve inputs before that.
    for appimage_input in "$@"; do
        [[ -f "$appimage_input" ]] || die "AppImage file not found: $appimage_input"
        appimage_inputs+=("$(realpath -- "$appimage_input")")
    done
    set -- "${appimage_inputs[@]}"
    previous_appimage=$(_pkg_appimage_previous) || die "Failed to identify installed AppImage"
    if [[ -n "$previous_appimage" ]]; then
        [[ $# -eq 1 ]] || die "Cannot map multiple new AppImages to one installed AppImage"
        [[ "$1" != "$(realpath -- "$HOME/AppImages/$previous_appimage")" ]] || die "Update input is the installed AppImage itself"
        pkg_appimage_rm --skip-appends "$previous_appimage" || die "Failed to remove previous AppImage: $previous_appimage"
    fi

    ( is_ubuntu || is_debian ) && {
        if [ "$VERSION_CODENAME" = "bookworm" ]; then 
            pkg_install libfuse2  # workaround for debian 12
        else
            pkg_install libfuse2t64; 
        fi
    }
    { ( is_fedora || is_ostree || is_rhel ) && pkg_install fuse; }
    { ( is_arch || is_cachy || is_solus ) && pkg_install fuse2; }
    prep_dir "$HOME/AppImages"
    if is_systemd; then
        # Use Gear Lever for systemd systems
        call_script gearlever
        local output
        output=$(echo "y" | flatpak run it.mijorus.gearlever --integrate "$@" 2>&1) || {
            echo "$output"
            fatal "Failed to integrate AppImage."
        }
        local appimage_name
        appimage_name=$(
            find "$HOME/AppImages" -maxdepth 1 -type f -printf '%T@ %f\n' 2>/dev/null |
                sort -nr |
                head -n1 |
                cut -d' ' -f2-
        )
        if [[ -n "$appimage_name" ]]; then
            _append_transmap "appimage $appimage_name"
        else
            nonfatal "Could not determine integrated AppImage filename."
        fi
    else
        # Manual integration for non-systemd systems
        for appimage_file in "$@"; do
            [[ -f "$appimage_file" ]] || fatal "AppImage file not found: $appimage_file"
            local appimage_basename=$(basename "$appimage_file")
            prep_create "$HOME/AppImages/$appimage_basename"
            cp -f "$appimage_file" "$HOME/AppImages/$appimage_basename"
            chmod +x "$HOME/AppImages/$appimage_basename"
            
            prep_tmp_noram
            local extract_dir
            extract_dir="$HOME/.cache/linuxtoys/tmp" || fatal "Failed to create temp directory for extraction"
            cd "$extract_dir" || fatal "Failed to change to temp directory"
            "$HOME/AppImages/$appimage_basename" --appimage-extract >/dev/null 2>&1 || \
                { nonfatal "Failed to extract AppImage: $appimage_basename"; rm -rf "$extract_dir"; continue; }
            local desktop_file
            desktop_file=$(find squashfs-root -name "*.desktop" -type f 2>/dev/null | head -1)
            if [[ -n "$desktop_file" && -f "$desktop_file" ]]; then
                prep_dir "$HOME/.local/share/applications"
                local desktop_basename=$(basename "$desktop_file")
                prep_create "$HOME/.local/share/applications/$desktop_basename"
                cp -f "$desktop_file" "$HOME/.local/share/applications/$desktop_basename" || \
                    fatal "Failed to copy desktop file"
            fi
            local icon_file
            icon_file=$(find squashfs-root \( -name "*.png" -o -name "*.svg" -o -name "*.xpm" \) -type f 2>/dev/null | head -1)
            if [[ -n "$icon_file" && -f "$icon_file" ]]; then
                prep_dir "$HOME/.local/share/icons"
                local icon_basename=$(basename "$icon_file")
                prep_create "$HOME/.local/share/icons/$icon_basename"
                cp -f "$icon_file" "$HOME/.local/share/icons/$icon_basename" || \
                    nonfatal "Failed to copy icon file"
            fi
            _append_transmap "appimage $appimage_basename"
        done
    fi
}

pkg_appimage_rm () {
    local skip_appends=0 appimage_file
    if [[ "${1:-}" == --skip-appends ]]; then
        skip_appends=1
        shift
    fi
    [[ $# -gt 0 ]] || return 0
    for appimage_file in "$@"; do
        [[ "$appimage_file" != */* && "$appimage_file" != .* && "$appimage_file" != -* ]] || return 1
    done
    if is_systemd; then
        # Use Gear Lever for removal on systemd systems
        (
            cd "$HOME/AppImages" || exit 1
            echo "y" | flatpak run it.mijorus.gearlever --remove "$@"
        ) || return $?
        for appimage_file in "$@"; do
            [[ ! -e "$HOME/AppImages/$appimage_file" && ! -L "$HOME/AppImages/$appimage_file" ]] || return 1
        done
        [[ $skip_appends -eq 1 ]] || _append_transmap "appimage rm $*"
    else
        # Manual removal for non-systemd systems
        for appimage_file in "$@"; do
            local appimage_basename=$(basename "$appimage_file")
            local appimage_name_without_ext="${appimage_basename%.*}"
            
            # Remove from AppImages directory
            if [[ -f "$HOME/AppImages/$appimage_basename" ]]; then
                rm -f -- "$HOME/AppImages/$appimage_basename" || return $?
                [[ $skip_appends -eq 1 ]] || _append_transmap "appimage rm $appimage_basename"
            fi
        done
    fi
    return 0
}

pkg_npm () {
    if ! command -v npm &>/dev/null; then
        sudo_rq
        { ( is_ubuntu || is_debian || is_suse ) && pkg_install npm; }
        { ( is_fedora || is_ostree ) && pkg_install nodejs-npm; }
        { ( is_rhel ) && rpmfusion_chk && pkg_install nodejs-npm; }
        { ( is_arch || is_cachy ) && pkg_install npm; }
    fi
    # PATH config
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$rc" ]; then
            # Check if PATH modification for .npm-global/bin already exists in the file
            if ! grep -E "PATH=.*/home/$USER/.npm-global/bin|/home/$USER/\.npm-global/bin" "$rc" > /dev/null 2>&1; then
                prep_edit "$rc"
                echo "export PATH=\"/home/$USER/.npm-global/bin:\$PATH\"" >> "$rc"
                export PATH="/home/$USER/.npm-global/bin:$PATH" # handle current term viewer only in case it's not already in PATH
            fi
        fi
    done
    # for fish shells
    fish_config="$HOME/.config/fish/config.fish"
    if [ -f "$fish_config" ]; then
        if ! grep -E "set.*PATH.*/home/$USER/.npm-global/bin|/home/$USER/\.npm-global/bin" "$fish_config" > /dev/null 2>&1; then
            prep_edit "$fish_config"
            echo "set -gx PATH /home/$USER/.npm-global/bin \$PATH" >> "$fish_config"
            export PATH="/home/$USER/.npm-global/bin:$PATH"
        fi
    fi  

    local -a flags=()
    local -a packages=()
    # Separate flags from package names, filtering out -g flag
    for arg in "$@"; do
        if [[ "$arg" == -* ]]; then
            if [[ "$arg" != "-g" && "$arg" != "--global" ]]; then
                flags+=("$arg")
            fi
        else
            packages+=("$arg")
        fi
    done
    for pkg in "${packages[@]}"; do
        if ! npm list -g "$pkg" &>/dev/null; then
            { npm install -g "${flags[@]}" "$pkg" 2>/dev/null || ( sudo_rq && sudo npm install -g "${flags[@]}" "$pkg" ) } || fatal "Failed to install npm package $pkg"
            _append_transmap "npm $pkg"
        fi
    done
}

pkg_bun () {
    if ! command -v bun &>/dev/null; then
        sudo_rq
        { curl -fsSL https://bun.sh/install | bash; } || fatal "Failed to install bun"
    else
        bun upgrade
    fi
    for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
        if [ -f "$rc" ]; then
            # Check if PATH modification for .bun/bin already exists in the file
            if ! grep -E "PATH=.*\/home\/$USER/.bun/bin|/home/$USER/.bun/bin" "$rc" > /dev/null 2>&1; then
                prep_edit "$rc"
                echo "export PATH=\"/home/$USER/.bun/bin:\$PATH\"" >> "$rc"
                export PATH="/home/$USER/.bun/bin:$PATH" # handle current term viewer only in case it's not already in PATH
            fi
        fi
    done
    # for fish shells
    fish_config="$HOME/.config/fish/config.fish"
    if [ -f "$fish_config" ]; then
        if ! grep -E "set.*PATH.*/home/$USER/.bun/bin|/home/$USER/.bun/bin" "$fish_config" > /dev/null 2>&1; then
            prep_edit "$fish_config"
            echo "set -gx PATH /home/$USER/.bun/bin \$PATH" >> "$fish_config"
            export PATH="/home/$USER/.bun/bin:$PATH"
        fi
    fi
    for pkg in "$@"; do
        if ! bun list -g "$pkg" &>/dev/null; then
            bun install -g "$pkg" || fatal "Failed to install bun package $pkg"
            _append_transmap "bun $pkg"
        fi
    done
}
