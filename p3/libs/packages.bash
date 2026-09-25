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
            { { [ "$UPD_SERVICE" = "1" ] && rm -f /var/lib/pacman/db.lck; } || sudo_ rm -f /var/lib/pacman/db.lck; } || die "Failed to remove stale lock. Run: sudo_ rm /var/lib/pacman/db.lck"
        fi
    fi
}
interrupted_apt_guard () {
    local needs_repair=0

    if [ -n "$(dpkg --audit 2>/dev/null)" ]; then
        info "An interrupted package operation was detected. Attempting recovery..."
        { { [ "$UPD_SERVICE" = "1" ] && dpkg --configure -a; } || sudo_ dpkg --configure -a; } || \
            die "Failed to recover interrupted dpkg operation. Manual user intervention required."
        needs_repair=1
    fi
    if ! { { [ "$UPD_SERVICE" = "1" ] && apt-get check; } || sudo_ apt-get check; } >/dev/null 2>&1; then
        info "Broken package dependencies were detected. Attempting recovery..."
        needs_repair=1
    fi

    if [ "$needs_repair" -eq 1 ]; then
        { { [ "$UPD_SERVICE" = "1" ] && apt-get --fix-broken install -y; } ||
            sudo_ apt-get --fix-broken install -y; } || die "Failed to fix broken packages. Manual user intervention required."
        apt-get check >/dev/null 2>&1 || die "Package dependencies remain broken. Manual user intervention required."
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
    # Handle --ignore-appends, --ostreecheck, --allowerasing, --bypass and --no-recommends flags
    local _ignore_appends=0
    local _ostreecheck=0
    local _allowerasing=0
    local _bypass=0
    local _no_recommends=0
    local -a _filtered_args=()

    for arg in "$@"; do
        if [[ "$arg" == "--ignore-appends" ]]; then
            _ignore_appends=1
        elif [[ "$arg" == "--ostreecheck" ]]; then
            _ostreecheck=1
        elif [[ "$arg" == "--allowerasing" ]]; then
            _allowerasing=1
        elif [[ "$arg" == "--bypass" ]]; then
            _bypass=1
        elif [[ "$arg" == "--no-recommends" ]]; then
            _no_recommends=1
        else
            _filtered_args+=("$arg")
        fi
    done

    pkg_exists "${_filtered_args[@]}"
    [[ ${#pkg_found[@]} -gt 0 ]] && echo "Packages ${pkg_found[*]} already installed, skipping."
    [[ ${#pkg_notfound[@]} -eq 0 ]] && return 0
    local to_install="${pkg_notfound[*]}"
    askpass
    (( _bypass )) || runner_lock "package-transaction"
    if is_debian || is_ubuntu; then
        interrupted_apt_guard
        if (( _no_recommends )); then
            sudo_ apt-get install -y --no-install-recommends "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        else
            sudo_ apt-get install -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        fi
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    elif is_arch || is_cachy || is_manjaro; then
        if ! is_manjaro; then
            if ! pacman-conf --repo-list 2>/dev/null | grep -qx 'extra'; then
                prep_edit /etc/pacman.conf
                printf '\n[extra]\nInclude = /etc/pacman.d/mirrorlist\n' |
                    sudo_ tee -a /etc/pacman.conf >/dev/null
            fi
            # fix #1255
            if [[ ! -e /var/lib/pacman/sync/extra.db ]]; then
                pacman_lock_guard
                sudo_ pacman -Sy --noconfirm || die "Failed to synchronize package databases"
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
                sudo_ pamac install --no-confirm "${_pacman_pkgs[@]}" || fatal "Failed to install $to_install_pacman"
                [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install_pacman"
            else
                pacman_lock_guard
                sudo_ pacman -S --noconfirm "${_pacman_pkgs[@]}" || fatal "Failed to install $to_install_pacman"
                [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install_pacman"
            fi
        fi
        if [ -n "$to_install_paru" ]; then
            if is_manjaro; then
                (( _bypass )) || runner_unlock
                pamac build --no-confirm "${_paru_pkgs[@]}" || die "Failed to install $to_install_paru"
                (( _bypass )) || runner_lock "package-transaction"
            else
                (( _bypass )) || runner_unlock
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
                    info "$parumsg"
                    call_script paru || die "Failed to repair paru"
                    paru --version >/dev/null 2>&1 || die "Paru is still unusable after reinstalling it"
                fi
                paru -S -a --noconfirm --skipreview "${_paru_pkgs[@]}" || die "Failed to install $to_install_paru"
                [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install_paru"
                (( _bypass )) || runner_lock "package-transaction"
            fi
        fi
    elif is_ostree; then
        sudo_ rpm-ostree install "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
        # Perform ostree check if requested and packages were actually installed
        if [[ $_ostreecheck -eq 1 && ${#pkg_notfound[@]} -gt 0 ]]; then
            zenwrn "$msgostreepending"
            exit 100
        fi
    elif is_fedora || is_rhel; then
        if [[ $_allowerasing -eq 1 ]]; then
            sudo_ dnf install -y --allowerasing "${pkg_notfound[@]}" || die "Failed to install $to_install"
        else
            sudo_ dnf install -y "${pkg_notfound[@]}" || die "Failed to install $to_install"
        fi
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    elif is_suse; then
        sudo_ zypper in -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    elif is_solus; then
        sudo_ eopkg it -y "${pkg_notfound[@]}" || fatal "Failed to install $to_install"
        [[ $_ignore_appends -eq 0 ]] && _append_transmap "pkg $to_install"
    fi
    (( _bypass )) || runner_unlock
}

# List installed Freedesktop runtime-extension refs in a stable, registry-friendly form.
# Runtime extensions may exist for several branches at once, so callers can use
# snapshots of this list to record what a single Flatpak transaction actually added.
_flatpak_runtime_extension_refs() {
    local scope="$1"
    flatpak list "$scope" --runtime --columns=application,arch,branch 2>/dev/null | \
        awk '$1 ~ /^org\.freedesktop\.Platform\./ { print $1 "/" $2 "/" $3 }' | \
        sort -u
}

_flatpak_runtime_extension_delta() {
    local before_file="$1"
    local scope="$2"
    comm -13 "$before_file" <(_flatpak_runtime_extension_refs "$scope")
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
        # Installing Flatpak or adding Flathub changes the AppStream source universe.
        # Keep the last completed catalog usable, but force the next AppStream check
        # to rebuild it against the newly available source.
        rm -f "$HOME/.cache/linuxtoys/appstream/state.json"
    fi
    local flatpak_scope="--user"
    if [[ $_skip_user -eq 1 ]]; then
        flatpak_scope="--system"
    elif flatpak remote-list --system 2>/dev/null | grep -q flathub && \
       ! flatpak remote-list --user 2>/dev/null | grep -q flathub; then
        flatpak_scope="--system"
    fi

    local -a _flatpak_normal=()
    local -a _flatpak_new=()
    local arg basename

    # Runtime extensions are transactional: install each requested ref separately
    # and register the exact branch(es) that appeared as a result of that transaction.
    for arg in "${_flatpak_args[@]}"; do
        basename="${arg%%/*}"
        if [[ "$basename" == org.freedesktop.Platform.* ]]; then
            local _runtime_before
            _runtime_before=$(mktemp)
            _flatpak_runtime_extension_refs "$flatpak_scope" > "$_runtime_before"

            if [[ "$flatpak_scope" == "--user" ]]; then
                flatpak install --or-update "$flatpak_scope" -y flathub "$arg" || {
                    rm -f "$_runtime_before"
                    fatal "Failed to install flatpak package $arg"
                }
            else
                flatpak install --or-update "$flatpak_scope" -y flathub "$arg" 2>/dev/null || {
                    sudo_ flatpak install --or-update "$flatpak_scope" -y flathub "$arg"
                } || {
                    rm -f "$_runtime_before"
                    fatal "Failed to install flatpak package $arg"
                }
            fi

            local -a _runtime_new=()
            mapfile -t _runtime_new < <(_flatpak_runtime_extension_delta "$_runtime_before" "$flatpak_scope")
            rm -f "$_runtime_before"
            if [[ ${#_runtime_new[@]} -gt 0 ]]; then
                _append_transmap "flatpak ${_runtime_new[*]}"
            fi
        else
            _flatpak_normal+=("$arg")
            if ! flatpak info "$flatpak_scope" "$arg" &>/dev/null; then
                _flatpak_new+=("$arg")
            fi
        fi
    done

    # Keep the existing batched path for ordinary applications/runtimes.
    if [[ ${#_flatpak_normal[@]} -gt 0 ]]; then
        if [[ "$flatpak_scope" == "--user" ]]; then
            flatpak install --or-update "$flatpak_scope" -y flathub "${_flatpak_normal[@]}" || \
                fatal "Failed to install flatpak packages ${_flatpak_normal[*]}"
        else
            flatpak install --or-update "$flatpak_scope" -y flathub "${_flatpak_normal[@]}" 2>/dev/null || \
                { sudo_ flatpak install --or-update "$flatpak_scope" -y flathub "${_flatpak_normal[@]}"; } || \
                fatal "Failed to install flatpak packages ${_flatpak_normal[*]}"
        fi

        for arg in "${_flatpak_normal[@]}"; do
            basename="${arg%%/*}"
            flatpak list "$flatpak_scope" --columns=application | grep -Fxq "$basename" || \
                fatal "Failed to install flatpak package $basename"
        done
        if [[ ${#_flatpak_new[@]} -gt 0 ]]; then
            _append_transmap "flatpak ${_flatpak_new[*]}"
        fi
    fi
}

pkg_fromfile () {
    # Handle flags that should not be passed to native package managers.
    local _ostreecheck=0
    local _skip_user=0
    local -a _filtered_args=()
    for arg in "$@"; do
        if [[ "$arg" == "--ostreecheck" ]]; then
            _ostreecheck=1
        elif [[ "$arg" == "--skip-user" ]]; then
            _skip_user=1
        else
            _filtered_args+=("$arg")
        fi
    done

    # Use filtered args for the rest of the function
    set -- "${_filtered_args[@]}"

    [[ "$1" == *.flatpak || "$1" == *.flatpakref ]] || askpass
    runner_lock "package-transaction"

    if [[ "$1" == *.flatpak || "$1" == *.flatpakref ]]; then
        if ! command -v flatpak &>/dev/null || ! flatpak remote-list | grep -q flathub; then
            summon_helpers
            flatpak_in_lib
        fi
        local flatpak_file="$1"
        local flatpak_scope="--user"
        if [[ $_skip_user -eq 1 ]]; then
            flatpak_scope="--system"
        elif flatpak remote-list --system 2>/dev/null | grep -q flathub && \
             ! flatpak remote-list --user 2>/dev/null | grep -q flathub; then
            flatpak_scope="--system"
        fi

        # Runtime-extension bundles commonly share one application ID across many
        # runtime branches. Snapshot the exact installed refs for each transaction.
        local _is_runtime_extension=0
        local _runtime_before=""
        local _runtime_before_system=""
        if [[ "$(basename "$flatpak_file")" == org.freedesktop.Platform.* ]]; then
            _is_runtime_extension=1
            _runtime_before=$(mktemp)
            _flatpak_runtime_extension_refs "$flatpak_scope" > "$_runtime_before"
            # A user-scope failure may legitimately fall back to system. Capture that
            # scope before the first attempt as well so its delta remains attributable.
            if [[ "$flatpak_scope" != "--system" ]]; then
                _runtime_before_system=$(mktemp)
                _flatpak_runtime_extension_refs --system > "$_runtime_before_system"
            fi
        fi

        # --or-update makes an already-installed bundle a successful no-op/update
        # instead of treating it as a reason to escalate to a system installation.
        local _flatpak_stderr
        if ! _flatpak_stderr=$(flatpak install --or-update "$flatpak_scope" --noninteractive "$flatpak_file" 2>&1 >/dev/null); then
            # A genuine fallback needs sudo. Authenticate while terminal input is
            # unlocked, then restore the package-transaction lock before continuing.
            runner_unlock
            askpass
            runner_lock "package-transaction"
            _flatpak_stderr=$(
                sudo_ flatpak install --or-update --system --noninteractive "$flatpak_file" 2>&1 >/dev/null
            ) || {
                [[ -n "$_runtime_before" ]] && rm -f "$_runtime_before"
                [[ -n "$_runtime_before_system" ]] && rm -f "$_runtime_before_system"
                fatal "Failed to install flatpak from file: $flatpak_file due to: $_flatpak_stderr"
            }
            # The successful fallback changed the effective scope. Use the system
            # snapshot captured before either attempt so the delta stays exact.
            if [[ $_is_runtime_extension -eq 1 && "$flatpak_scope" != "--system" ]]; then
                rm -f "$_runtime_before"
                _runtime_before="$_runtime_before_system"
                _runtime_before_system=""
            fi
            flatpak_scope="--system"
        fi

        if [[ $_is_runtime_extension -eq 1 ]]; then
            local -a _runtime_new=()
            mapfile -t _runtime_new < <(_flatpak_runtime_extension_delta "$_runtime_before" "$flatpak_scope")
            rm -f "$_runtime_before"
            [[ -n "$_runtime_before_system" ]] && rm -f "$_runtime_before_system"
            if [[ ${#_runtime_new[@]} -gt 0 ]]; then
                _append_transmap "flatpak ${_runtime_new[*]}"
            fi
        else
            _append_transmap "pkg file $flatpak_file"
        fi
        runner_unlock
        return 0
    fi

    if is_debian || is_ubuntu; then
        { sudo_ apt-get -o APT::Sandbox::User=root install -y "${@}" || sudo_ dpkg -i "${@}"; } || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    elif { is_arch || is_cachy; } && ! is_manjaro; then
        # check for lock before installing local package
        pacman_lock_guard
        if sudo_ pacman -U --noconfirm "${@}"; then
            _append_transmap "pkg file $*"
        else
            if [ -f PKGBUILD ]; then
                local pkgname=$(grep "^pkgname=" PKGBUILD | head -1 | cut -d'=' -f2 | tr -d "'\"")
                makepkg -si || die "Failed to build and install package $pkgname"
                _append_transmap "pkg file $pkgname"
            else
                fatal "Failed to install package $*"
            fi
        fi
    elif is_manjaro; then
        { sudo_ pamac install --no-confirm "./${*}" && _append_transmap "pkg file $*"; } || fatal "Failed to install package $*"
    elif is_ostree; then
        sudo_ rpm-ostree install "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
        # Perform ostree check if requested
        if [[ $_ostreecheck -eq 1 ]]; then
            zenwrn "$msgostreepending"
            exit 100
        fi
    elif is_fedora || is_rhel; then
        sudo_ dnf install -y "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    elif is_suse; then
        sudo_ zypper in -y "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    elif is_solus; then
        sudo_ eopkg it -y "${@}" || fatal "Failed to install $*"
        _append_transmap "pkg file $*"
    fi
    runner_unlock
}

pkg_tarball () {
    [[ $# -gt 0 ]] || die "No tarball files provided"

    # Avoid exposing a stale path if a later tarball operation fails before
    # completing successfully.
    unset LINUXTOYS_TARBALL_DIR

    local archive archive_name app_name apps_dir staging_dir source_path target_path
    local member normalized first_component common_root has_nested
    local -a members=()

    apps_dir="$HOME/.local/linuxtoys/apps"
    mkdir -p -- "$apps_dir" || die "Failed to create application directory: $apps_dir"

    for archive in "$@"; do
        [[ -f "$archive" ]] || die "Tarball file not found: $archive"

        archive="$(realpath -- "$archive")" || die "Failed to resolve tarball path: $archive"
        archive_name="$(basename -- "$archive")"

        case "$archive_name" in
            *.[Tt][Aa][Rr].[Gg][Zz])
                app_name="${archive_name:0:${#archive_name}-7}"
                ;;
            *.[Tt][Aa][Rr].[Xx][Zz])
                app_name="${archive_name:0:${#archive_name}-7}"
                ;;
            *)
                die "Unsupported tarball format: $archive_name"
                ;;
        esac

        [[ -n "$app_name" && "$app_name" != "." && "$app_name" != ".." ]] || \
            die "Could not derive application name from tarball: $archive_name"

        mapfile -t members < <(tar -tf "$archive") || \
            die "Failed to inspect tarball: $archive_name"
        [[ ${#members[@]} -gt 0 ]] || die "Tarball is empty: $archive_name"

        # Reject absolute paths and parent traversal before extracting.
        for member in "${members[@]}"; do
            normalized="${member#./}"
            [[ -n "$normalized" ]] || continue
            if [[ "$normalized" == /* || "$normalized" == ".." || \
                  "$normalized" == ../* || "$normalized" == */../* || \
                  "$normalized" == */.. ]]; then
                die "Unsafe path in tarball $archive_name: $member"
            fi
        done

        # If everything already lives below one top-level directory, preserve it
        # instead of adding another directory around it.
        common_root=""
        has_nested=0
        for member in "${members[@]}"; do
            normalized="${member#./}"
            normalized="${normalized%/}"
            [[ -n "$normalized" ]] || continue

            first_component="${normalized%%/*}"
            if [[ -z "$common_root" ]]; then
                common_root="$first_component"
            elif [[ "$first_component" != "$common_root" ]]; then
                common_root=""
                break
            fi

            [[ "$normalized" == */* ]] && has_nested=1
        done

        staging_dir=$(mktemp -d "$apps_dir/.tarball.XXXXXX") || \
            die "Failed to create tarball staging directory"

        tar --no-same-owner --no-same-permissions -xf "$archive" -C "$staging_dir" || {
            rm -rf -- "$staging_dir"
            die "Failed to extract tarball: $archive_name"
        }

        if [[ -n "$common_root" && $has_nested -eq 1 && -d "$staging_dir/$common_root" ]]; then
            app_name="$common_root"
            source_path="$staging_dir/$common_root"
        else
            source_path="$staging_dir"
        fi

        case "$app_name" in
            ''|.|..|*/*|*\\*)
                rm -rf -- "$staging_dir"
                die "Unsafe application directory name derived from tarball: $app_name"
                ;;
        esac

        target_path="$apps_dir/$app_name"

        # A rerun is an update: replace the previous tree completely so files
        # removed upstream do not linger after upgrading.
        rm -rf -- "$target_path" || {
            rm -rf -- "$staging_dir"
            die "Failed to replace previous application directory: $target_path"
        }

        if [[ "$source_path" == "$staging_dir" ]]; then
            mv -- "$staging_dir" "$target_path" || {
                rm -rf -- "$staging_dir"
                die "Failed to install tarball application: $app_name"
            }
        else
            mv -- "$source_path" "$target_path" || {
                rm -rf -- "$staging_dir"
                die "Failed to install tarball application: $app_name"
            }
            rm -rf -- "$staging_dir"
        fi

        # Expose the final installation directory to any post-install hook
        # running later in the same LinuxToys script.
        export LINUXTOYS_TARBALL_DIR="$target_path"

        _append_transmap "tarball $app_name"
    done
}

pkg_binary () {
    [ "$#" -eq 1 ] || die "Usage: pkg_binary BINARY_FILE"

    # Avoid exposing a stale path if a later binary operation fails before
    # completing successfully.
    unset LINUXTOYS_BIN_DIR

    local binary="$1"
    local app_name="${LINUXTOYS_APP_NAME:-}"
    local apps_dir="$HOME/.local/linuxtoys/apps"
    local target_dir target_file

    [ -f "$binary" ] || die "Binary file not found: $binary"
    [ -n "$app_name" ] || die "LinuxToys app name is unavailable"

    # The display name is also the single-binary installation directory name.
    # Reject path components rather than allowing app metadata to escape apps_dir.
    case "$app_name" in
        ''|.|..|*/*|*\\*) die "Unsafe LinuxToys app name for binary installation: $app_name" ;;
    esac

    binary=$(realpath -- "$binary") || die "Failed to resolve binary path: $binary"
    target_dir="$apps_dir/$app_name"
    target_file="$target_dir/$(basename -- "$binary")"

    mkdir -p -- "$apps_dir" || die "Failed to create application directory: $apps_dir"

    # Preserve update reversibility just like other filesystem operations.
    if [ -d "$target_dir" ]; then
        prep_dir_edit "$target_dir"
        rm -rf -- "$target_dir" || die "Failed to replace previous binary application directory: $target_dir"
        mkdir -p -- "$target_dir" || die "Failed to recreate binary application directory: $target_dir"
    else
        prep_dir "$target_dir"
    fi

    cp -- "$binary" "$target_file" || die "Failed to install binary: $binary"
    chmod +x -- "$target_file" || die "Failed to make binary executable: $target_file"

    # Expose the final installation directory to any post-install hook
    # running later in the same LinuxToys script.
    export LINUXTOYS_BIN_DIR="$target_dir"

    desktop_shortcut "\"$target_file\""
}

pkg_fromurl () {
    [[ $# -gt 0 ]] || die "No package URLs provided"

    local _tarball=0 _binary=0 _skip_user=0 arg
    local -a urls=()
    for arg in "$@"; do
        case "$arg" in
            --tar|--tarball)
                _tarball=1
                ;;
            --bin|--binary)
                _binary=1
                ;;
            --skip-user)
                _skip_user=1
                ;;
            *)
                urls+=("$arg")
                ;;
        esac
    done
    [[ ${#urls[@]} -gt 0 ]] || die "No package URLs provided"
    [[ $_tarball -eq 0 || $_binary -eq 0 ]] || die "--tar and --bin cannot be used together"
    [[ $_binary -eq 0 || ${#urls[@]} -eq 1 ]] || die "pkg_fromurl --bin expects exactly one URL"

    local url filename download_dir package_dir package_file
    local effective_url content_disposition metadata_file temp_file
    local -a package_files=()

    prep_tmp_noram
    download_dir=$(mktemp -d ./pkg_fromurl.XXXXXX) || {
        die "Failed to create package download directory"
    }

    for url in "${urls[@]}"; do
        temp_file="$download_dir/${#package_files[@]}.download"
        metadata_file="$download_dir/${#package_files[@]}.metadata"

        curl -fL --retry 3 \
            --output "$temp_file" \
            --write-out '%{url_effective}\n%header{content-disposition}\n' \
            -- "$url" > "$metadata_file" || {
                rm -f -- "$temp_file" "$metadata_file"
                die "Failed to download package: $url"
            }

        effective_url=$(sed -n '1p' "$metadata_file")
        content_disposition=$(sed -n '2p' "$metadata_file")
        rm -f -- "$metadata_file"

        # Prefer a filename supplied explicitly by the server.
        filename=""
        if [[ "$content_disposition" =~ filename=\"([^\"]+)\" ]]; then
            filename="${BASH_REMATCH[1]}"
        elif [[ "$content_disposition" =~ filename=([^;\ ]+) ]]; then
            filename="${BASH_REMATCH[1]}"
        fi

        # Otherwise derive it from the final URL after redirects.
        if [[ -z "$filename" ]]; then
            filename="${effective_url%%[?#]*}"
            filename="${filename##*/}"
        fi

        # Fall back to the original URL if the redirect target also lacks a name.
        if [[ -z "$filename" || "$filename" == "." || "$filename" == ".." ]]; then
            filename="${url%%[?#]*}"
            filename="${filename##*/}"
        fi

        case "$filename" in
            ''|.|..|*/*|*\\*)
                rm -f -- "$temp_file"
                die "Package URL has no valid filename: $url"
                ;;
        esac

        if [[ $_tarball -eq 1 ]]; then
            case "$filename" in
                *.[Tt][Aa][Rr].[Gg][Zz]|*.[Tt][Aa][Rr].[Xx][Zz]) ;;
                *)
                    rm -f -- "$temp_file"
                    die "Tarball URL did not resolve to a .tar.gz or .tar.xz file: $url"
                    ;;
            esac
        fi

        # SteamOS must never hand a native package to pkg_fromfile. Explicit
        # --tar/--bin modes are user-level installs and are allowed; otherwise
        # the resolved download must be an AppImage or Flatpak file.
        if is_steamos && [[ $_tarball -eq 0 && $_binary -eq 0 ]]; then
            case "$filename" in
                *.[Aa][Pp][Pp][Ii][Mm][Aa][Gg][Ee]|*.[Ff][Ll][Aa][Tt][Pp][Aa][Kk]) ;;
                *)
                    rm -f -- "$temp_file"
                    die "SteamOS only supports AppImage, Flatpak, tarball, or single-binary installs from URLs: $filename"
                    ;;
            esac
        fi

        # Keep the server-provided basename intact. A per-download subdirectory
        # avoids collisions when more than one URL resolves to the same name.
        package_dir="$download_dir/${#package_files[@]}"
        mkdir -p -- "$package_dir" || die "Failed to prepare package download directory"
        package_file="$package_dir/$filename"

        mv -- "$temp_file" "$package_file" || {
            rm -f -- "$temp_file"
            die "Failed to prepare downloaded package: $filename"
        }

        package_files+=("$package_file")
    done

    for package_file in "${package_files[@]}"; do
        if [[ $_binary -eq 1 ]]; then
            pkg_binary "$package_file"
            continue
        fi

        if [[ $_tarball -eq 1 ]]; then
            pkg_tarball "$package_file"
            continue
        fi

        case "$package_file" in
            *.[Aa][Pp][Pp][Ii][Mm][Aa][Gg][Ee])
                pkg_appimage "$package_file"
                ;;
            *)
                if [[ $_skip_user -eq 1 ]]; then
                    pkg_fromfile --skip-user "$package_file"
                else
                    pkg_fromfile "$package_file"
                fi
                ;;
        esac
    done
}

pkg_make () {
    [[ $# -gt 0 ]] || die "Usage: pkg_make [--command INSTALL_COMMAND] [--tar REPOSITORY_URL [ASSET_GLOB] | --url TARBALL_URL | --uninstall SOURCE_URL | REPOSITORY_URL]"

    unset LINUXTOYS_MAKE_DIR

    local mode="git" uninstall=0 source="" selector="" install_command="sudo make install"
    local arg
    local -a args=() build_dependencies=()

    # A custom command is kept as one argument and executed from the directory
    # containing the Makefile. The uninstall path derives the matching command
    # by replacing the install target with its uninstall counterpart.
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --command)
                shift
                [[ $# -gt 0 ]] || die "pkg_make --command requires an install command"
                install_command="$1"
                ;;
            --dependency)
                shift
                [[ $# -gt 0 ]] || die "pkg_make --dependency requires a package name"
                build_dependencies+=("$1")
                ;;
            *)
                args+=("$1")
                ;;
        esac
        shift
    done
    set -- "${args[@]}"
    [[ $# -gt 0 ]] || die "pkg_make requires a source"
    [[ -n "${install_command//[[:space:]]/}" ]] || die "pkg_make install command cannot be empty"

    case "$1" in
        --tar|--tarball)
            mode="release-tar"
            shift
            [[ $# -ge 1 && $# -le 2 ]] || die "Usage: pkg_make [--command INSTALL_COMMAND] --tar REPOSITORY_URL [ASSET_GLOB]"
            source="$1"
            selector="${2:-*}"
            ;;
        --url)
            mode="tar-url"
            shift
            [[ $# -eq 1 ]] || die "Usage: pkg_make [--command INSTALL_COMMAND] --url TARBALL_URL"
            source="$1"
            ;;
        --uninstall)
            uninstall=1
            shift
            [[ $# -eq 1 ]] || die "Usage: pkg_make [--command INSTALL_COMMAND] --uninstall SOURCE_URL"
            source="$1"
            case "${source%%[?#]*}" in
                *.tar.gz|*.tar.xz) mode="tar-url" ;;
                *) mode="git" ;;
            esac
            ;;
        *)
            [[ $# -eq 1 ]] || die "Usage: pkg_make [--command INSTALL_COMMAND] REPOSITORY_URL"
            source="$1"
            ;;
    esac

    # Release tarball selection deliberately reuses pkg_fromrelease so make
    # installs follow exactly the same stable-release, architecture and asset
    # selection rules as every other LinuxToys release install.
    if [[ "$mode" == "release-tar" ]]; then
        local -a release_make_args=(--make --make-command "$install_command")
        for arg in "${build_dependencies[@]}"; do
            release_make_args+=(--make-dependency "$arg")
        done
        pkg_fromrelease "${release_make_args[@]}" "$source" "$selector"
        return $?
    fi

    [[ "$source" == https://* ]] || die "pkg_make only accepts HTTPS sources"

    local user_level_make=0 steamos_readonly_toggled=0
    if [[ ! "$install_command" =~ (^|[[:space:];|&()])sudo([[:space:]]|$) ]]; then
        user_level_make=1
    fi

    if is_steamos && (( user_level_make )); then
        # User-level Make applications are SteamOS-compatible. Their declared
        # native dependencies are treated as build-only Arch packages. Temporarily
        # unlock the system image only while installing the build toolchain.
        local -a steamos_build_packages=(base-devel)
        if (( ! uninstall )); then
            steamos_build_packages+=("${build_dependencies[@]}")
        fi

                command -v steamos-readonly >/dev/null 2>&1 || \
            die "steamos-readonly is required for pkg_make on SteamOS"

        if steamos-readonly status 2>/dev/null | grep -qi 'enabled'; then
            sudo_ steamos-readonly disable || die "Failed to disable SteamOS read-only mode"
            steamos_readonly_toggled=1
        fi

        pacman_lock_guard
        if ! sudo_ pacman -S --needed --noconfirm "${steamos_build_packages[@]}"; then
            if (( steamos_readonly_toggled )); then
                sudo_ steamos-readonly enable || warn "Failed to restore SteamOS read-only mode after package installation failure"
            fi
            die "Failed to install SteamOS make build dependencies"
        fi

        if (( steamos_readonly_toggled )); then
            sudo_ steamos-readonly enable || die "Failed to restore SteamOS read-only mode"
            steamos_readonly_toggled=0
        fi
    else
        if ! command -v make >/dev/null 2>&1; then
                        pkg_install --ostreecheck make
        fi
        if (( ! uninstall && ${#build_dependencies[@]} > 0 )); then
                        pkg_install --ostreecheck --ignore-appends "${build_dependencies[@]}"
        fi
    fi

    local workdir source_dir archive make_dir run_command="$install_command"
    local -a makefiles=()
    prep_tmp_noram
    workdir=$(mktemp -d ./pkg_make.XXXXXX) || die "Failed to create make build directory"

    if [[ "$mode" == "git" ]]; then
        command -v git >/dev/null 2>&1 || die "git is required for pkg_make repository installs"
        git clone --depth 1 -- "$source" "$workdir/source" || {
            rm -rf -- "$workdir"
            die "Failed to clone make source: $source"
        }
        source_dir="$workdir/source"
    else
        archive="$workdir/source.tar"
        curl -fL --retry 3 \
            --proto '=https' \
            --tlsv1.2 \
            --output "$archive" \
            -- "$source" || {
            rm -rf -- "$workdir"
            die "Failed to download make source: $source"
        }

        # Reject archive path traversal before extraction.
        local member normalized
        while IFS= read -r member; do
            normalized="${member#./}"
            [[ -n "$normalized" ]] || continue
            if [[ "$normalized" == /* || "$normalized" == ".." || \
                  "$normalized" == ../* || "$normalized" == */../* || \
                  "$normalized" == */.. ]]; then
                rm -rf -- "$workdir"
                die "Unsafe path in make tarball: $member"
            fi
        done < <(tar -tf "$archive") || {
            rm -rf -- "$workdir"
            die "Failed to inspect make tarball: $source"
        }

        source_dir="$workdir/source"
        mkdir -p -- "$source_dir" || die "Failed to create make extraction directory"
        tar --no-same-owner --no-same-permissions -xf "$archive" -C "$source_dir" || {
            rm -rf -- "$workdir"
            die "Failed to extract make tarball: $source"
        }
    fi

    # Prefer a top-level makefile. If there is none, accept exactly one makefile
    # in the fetched tree rather than guessing between unrelated subprojects.
    if [[ -f "$source_dir/Makefile" || -f "$source_dir/makefile" || -f "$source_dir/GNUmakefile" ]]; then
        make_dir="$source_dir"
    else
        mapfile -t makefiles < <(find "$source_dir" -type f \
            \( -iname 'Makefile' -o -iname 'GNUmakefile' \) -print 2>/dev/null)
        [[ ${#makefiles[@]} -gt 0 ]] || {
            rm -rf -- "$workdir"
            die "No Makefile found in make source: $source"
        }
        [[ ${#makefiles[@]} -eq 1 ]] || {
            rm -rf -- "$workdir"
            die "Multiple Makefiles found in make source; unable to choose safely"
        }
        make_dir="$(dirname -- "${makefiles[0]}")"
    fi

    export LINUXTOYS_MAKE_DIR="$make_dir"

    if (( uninstall )); then
        # Keep the install flow intact and only turn the Make install target into
        # its uninstall equivalent: install -> uninstall, install-user -> uninstall-user.
        run_command=$(python3 - "$install_command" <<'PY2'
import re
import sys

command = sys.argv[1]
updated, count = re.subn(r'(?<![A-Za-z0-9_])install(?=$|[-_]|[^A-Za-z0-9_])', 'uninstall', command, count=1)
if count != 1:
    sys.exit(1)
print(updated)
PY2
        ) || {
            rm -rf -- "$workdir"
            die "Unable to derive make uninstall command from: $install_command"
        }
    fi

    if (( ! uninstall )); then
        make -C "$make_dir" || {
            die "Failed to build make source: $source"
        }
    fi

    # Only prompt for authentication when this flow actually invokes sudo.
    if [[ "$run_command" =~ (^|[[:space:];|&()])sudo([[:space:]]|$) ]]; then
        askpass
    fi
    runner_lock "package-transaction"

    ( cd -- "$make_dir" && bash -c "$run_command" ) || {
        runner_unlock
        rm -rf -- "$workdir"
        if (( uninstall )); then
            die "Failed to uninstall make source: $source"
        else
            die "Failed to install make source: $source"
        fi
    }

    if (( ! uninstall )); then
        local encoded_command
        encoded_command=$(printf '%s' "$install_command" | base64 -w 0) || die "Failed to encode make install command"
        _append_transmap "pkg make $source cmd64:$encoded_command"
    fi

    runner_unlock
}

pkg_fromrelease () {
    local _tarball=0 _binary=0 _make=0 arg make_command="sudo make install"
    local -a release_args=() make_dependencies=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --tar|--tarball)
                _tarball=1
                ;;
            --bin|--binary)
                _binary=1
                ;;
            --make)
                _make=1
                _tarball=1
                ;;
            --make-command)
                shift
                [[ $# -gt 0 ]] || die "pkg_fromrelease --make-command requires a command"
                make_command="$1"
                ;;
            --make-dependency)
                shift
                [[ $# -gt 0 ]] || die "pkg_fromrelease --make-dependency requires a package name"
                make_dependencies+=("$1")
                ;;
            *)
                release_args+=("$1")
                ;;
        esac
        shift
    done
    set -- "${release_args[@]}"

    [[ $# -ge 1 && $# -le 2 ]] || die "Usage: pkg_fromrelease [--tar|--bin|--make] REPOSITORY_URL [ASSET_NAME_OR_GLOB]"
    [[ $_tarball -eq 0 || $_binary -eq 0 ]] || die "--tar and --bin cannot be used together"
    [[ $_make -eq 0 || $_binary -eq 0 ]] || die "--make and --bin cannot be used together"
    [[ $_binary -eq 0 || $# -eq 2 ]] || die "pkg_fromrelease --bin requires the exact release asset name"

    local native_type="" package_url
    local -a release_selection
    if is_steamos; then
        native_type=""
    elif is_arch || is_cachy; then
        native_type=arch
    elif is_fedora || is_rhel || is_ostree; then
        native_type=rpm
    elif is_debian || is_ubuntu; then
        native_type=deb
    elif is_solus; then
        native_type=eopkg
    fi

    package_url=$(python3 - "$1" "${2:-*}" "$native_type" "$(uname -m)" "$_tarball" "$_binary" <<'PY'
import fnmatch
import json
import re
import subprocess
import sys
from urllib.parse import quote, unquote, urlsplit


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def repository_api(repository):
    try:
        parsed = urlsplit(repository)
    except ValueError:
        fail("Invalid repository URL")

    if parsed.scheme != "https" or parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port:
        fail("Repository URL must be a plain HTTPS GitHub, Codeberg, or GitLab project URL")

    host = (parsed.hostname or "").lower()
    path = unquote(parsed.path).strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    parts = path.split("/") if path else []

    if any(not part or part in (".", "..") for part in parts):
        fail("Invalid repository name")

    if host in ("github.com", "codeberg.org"):
        if len(parts) != 2:
            fail(f"Expected https://{host}/OWNER/REPO")
        owner, repo = parts
        base = "https://api.github.com" if host == "github.com" else "https://codeberg.org/api/v1"
        return host, f"{base}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/releases/latest"

    if host == "gitlab.com":
        if len(parts) < 2:
            fail("Expected https://gitlab.com/NAMESPACE/PROJECT")
        project = quote("/".join(parts), safe="")
        return host, f"https://gitlab.com/api/v4/projects/{project}/releases/permalink/latest"

    fail("Expected a github.com, codeberg.org, or gitlab.com repository URL")


def normalize_release(host, release):
    if not isinstance(release, dict):
        fail("Release API returned invalid data")

    if host != "gitlab.com":
        if not isinstance(release.get("assets"), list):
            fail("Release API returned no asset list")
        if release.get("draft") or release.get("prerelease"):
            fail("Latest release is not a stable published release")
        return release

    gitlab_assets = release.get("assets", {})
    links = gitlab_assets.get("links", []) if isinstance(gitlab_assets, dict) else []
    if not isinstance(links, list):
        fail("Release API returned no asset list")

    assets = []
    for link in links:
        if not isinstance(link, dict):
            continue
        name = link.get("name", "")
        url = link.get("direct_asset_url") or link.get("url", "")
        if isinstance(name, str) and isinstance(url, str):
            assets.append({"name": name, "browser_download_url": url})

    normalized = dict(release)
    normalized["assets"] = assets
    return normalized


repository, pattern, native, machine, tarball_mode, binary_mode = sys.argv[1:]
tarball_mode = tarball_mode == "1"
binary_mode = binary_mode == "1"
host, api = repository_api(repository)
try:
    response = subprocess.run(
        ["curl", "-fsSL", "--retry", "3", "--connect-timeout", "15",
         "--max-time", "60", "-H", "Accept: application/json", "--", api],
        check=True, capture_output=True, text=True,
    )
    release = normalize_release(host, json.loads(response.stdout))
except (OSError, subprocess.CalledProcessError, ValueError) as error:
    fail(f"Failed to fetch latest release from {repository}: {error}")
version = release.get("tag_name", "")
if not isinstance(version, str) or not version:
    fail("Latest release has no tag name")
pattern = pattern.replace("$APP_GIT_VERSION", version)

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
if binary_mode:
    formats = None
elif tarball_mode:
    formats = [(".tar.gz", ".tar.xz")]
else:
    formats = [(".appimage",), (".flatpak",), native_extensions.get(native, ())]
candidates = []
for asset in release["assets"]:
    name, url = asset.get("name", ""), asset.get("browser_download_url", "")
    if not isinstance(name, str) or not isinstance(url, str):
        continue
    lower = name.lower()
    if urlsplit(url).scheme != "https":
        continue
    if binary_mode:
        if name != pattern:
            continue
    elif not fnmatch.fnmatchcase(lower, pattern.lower()):
        continue
    if re.search(r"(?:^|[._-])(?:debug|debuginfo|debugsource|devel|source|src)(?:[._-]|$)", lower):
        continue
    if binary_mode:
        kind = 0
    else:
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
print(f"Selected {best[0][1]} from {version}", file=sys.stderr)
print(version)
print(best[0][2])
PY
    ) || die "Failed to select a release package"

    mapfile -t release_selection <<< "$package_url"
    [[ ${#release_selection[@]} -eq 2 ]] || die "Failed to read release selection"
    export APP_GIT_VERSION="${release_selection[0]}"
    package_url="${release_selection[1]}"

    if [[ $_make -eq 1 ]]; then
        local -a make_args=(--command "$make_command")
        for arg in "${make_dependencies[@]}"; do
            make_args+=(--dependency "$arg")
        done
        pkg_make "${make_args[@]}" --url "$package_url"
    elif [[ $_binary -eq 1 ]]; then
        pkg_fromurl --bin "$package_url"
    elif [[ $_tarball -eq 1 ]]; then
        pkg_fromurl --tar "$package_url"
    else
        pkg_fromurl "$package_url"
    fi

    # Repository-list release metadata is informational registry state. Record it
    # only after the selected asset was installed successfully.
    if [[ -n "${LINUXTOYS_REPO_APP_ID:-}" ]]; then
        _append_transmap "git-release ${LINUXTOYS_REPO_APP_ID} ${APP_GIT_VERSION} $1"
    fi
}

latest_release_version () {
    [[ $# -eq 1 ]] || { echo "Usage: latest_release_version REPOSITORY_URL" >&2; return 2; }

    python3 - "$1" <<'PY'
import json
import subprocess
import sys
from urllib.parse import quote, unquote, urlsplit

repository = sys.argv[1]
try:
    parsed = urlsplit(repository)
except ValueError:
    sys.exit(2)

if parsed.scheme != "https" or parsed.query or parsed.fragment or parsed.username or parsed.password or parsed.port:
    sys.exit(2)

host = (parsed.hostname or "").lower()
path = unquote(parsed.path).strip("/")
if path.endswith(".git"):
    path = path[:-4]
parts = path.split("/") if path else []
if any(not part or part in (".", "..") for part in parts):
    sys.exit(2)

if host in ("github.com", "codeberg.org"):
    if len(parts) != 2:
        sys.exit(2)
    owner, repo = parts
    base = "https://api.github.com" if host == "github.com" else "https://codeberg.org/api/v1"
    api = f"{base}/repos/{quote(owner, safe='')}/{quote(repo, safe='')}/releases/latest"
elif host == "gitlab.com":
    if len(parts) < 2:
        sys.exit(2)
    project = quote("/".join(parts), safe="")
    api = f"https://gitlab.com/api/v4/projects/{project}/releases/permalink/latest"
else:
    sys.exit(2)

try:
    response = subprocess.run(
        ["curl", "-fsSL", "--retry", "3", "--connect-timeout", "15",
         "--max-time", "60", "-H", "Accept: application/json", "--", api],
        check=True, capture_output=True, text=True,
    )
    release = json.loads(response.stdout)
except (OSError, subprocess.CalledProcessError, ValueError):
    sys.exit(1)

if not isinstance(release, dict):
    sys.exit(1)
if host != "gitlab.com" and (release.get("draft") or release.get("prerelease")):
    sys.exit(1)

version = release.get("tag_name", "")
if not isinstance(version, str) or not version:
    sys.exit(1)

print(version)
PY
}

pkg_remove () {
    pkg_exists "$@"
    [[ ${#pkg_found[@]} -eq 0 ]] && return 0
    local to_remove="${pkg_found[*]}"

    # Manjaro uses pamac directly here; other native removals escalate.
    is_manjaro || askpass
    runner_lock "package-transaction"

    if is_debian || is_ubuntu; then
        sudo_ apt-get remove -y --allow-unauthenticated "${pkg_found[@]}" \
            || fatal "Failed to remove packages: $to_remove"
    elif { is_arch || is_cachy; } && ! is_manjaro; then
        pacman_lock_guard
        sudo_ pacman -Rsn --noconfirm "${pkg_found[@]}" \
            || fatal "Failed to remove packages: $to_remove"
    elif is_manjaro; then
        pamac remove --no-confirm "${pkg_found[@]}" \
            || fatal "Failed to remove packages: $to_remove"
    elif is_ostree; then
        sudo_ rpm-ostree uninstall "${pkg_found[@]}" \
            || fatal "Failed to remove packages: $to_remove"
    elif is_fedora || is_rhel; then
        sudo_ dnf remove -y "${pkg_found[@]}" \
            || fatal "Failed to remove packages: $to_remove"
    elif is_suse; then
        sudo_ zypper rm -y "${pkg_found[@]}" \
            || fatal "Failed to remove packages: $to_remove"
    elif is_solus; then
        sudo_ eopkg rmf -y "${pkg_found[@]}" \
            || fatal "Failed to remove packages: $to_remove"
    fi

    runner_unlock

    _append_transmap "pkg rm $to_remove"
}
pkg_rm () { pkg_remove "$@"; }

_pkg_appimage_gearlever_previous () {
    local app_name="${LINUXTOYS_APP_NAME:-}"
    [[ -n "$app_name" ]] || return 0

    flatpak run it.mijorus.gearlever --list-installed 2>/dev/null |
        awk -v target="$app_name" '
        {
            # Gear Lever ends each record with the absolute AppImage path.
            path = $NF

            # Everything preceding " (" at the beginning is the app name.
            line = $0
            sub(/[[:space:]]+\([^)]*\).*/, "", line)

            if (line == target) {
                print path
                exit
            }
        }'
}

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
        appimage_input="$(realpath -- "$appimage_input")" || die "Failed to resolve AppImage path: $appimage_input"
        chmod +x -- "$appimage_input" || die "Failed to make AppImage executable: $appimage_input"
        appimage_inputs+=("$appimage_input")
    done
    set -- "${appimage_inputs[@]}"
    previous_appimage=$(_pkg_appimage_previous) || die "Failed to identify installed AppImage"
    # No LinuxToys-owned copy: look for an existing Gear Lever installation.
    if [[ -z "$previous_appimage" && -n "${LINUXTOYS_APP_NAME:-}" ]] && is_systemd; then
        local gearlever_path
        gearlever_path=$(_pkg_appimage_gearlever_previous) || die "Failed to query Gear Lever AppImages"
        if [[ -n "$gearlever_path" ]]; then
            case "$gearlever_path" in
                "$HOME/AppImages/"*) previous_appimage="${gearlever_path##*/}" ;;
                *) die "Gear Lever returned an unexpected AppImage path: $gearlever_path" ;;
            esac
        fi
    fi
    if [[ -n "$previous_appimage" ]]; then
        [[ $# -eq 1 ]] || die "Cannot map multiple new AppImages to one installed AppImage"
        [[ "$1" != "$(realpath -- "$HOME/AppImages/$previous_appimage")" ]] || die "Update input is the installed AppImage itself"
        pkg_appimage_rm --skip-appends "$previous_appimage" || die "Failed to remove previous AppImage: $previous_appimage"
    fi

    { is_ubuntu || is_debian; } && {
        if [ "$VERSION_CODENAME" = "bookworm" ]; then
            pkg_exists libfuse2
            [[ ! ${#pkg_notfound[@]} -eq 0 ]] && {
                pkg_install libfuse2  # workaround for debian 12
            }
        else
            pkg_exists libfuse2
            [[ ! ${#pkg_notfound[@]} -eq 0 ]] && {
                                if ! apt-cache --no-all-versions show libfuse2t64 >/dev/null 2>&1; then # probably forky/testing
                    sudo_ mkdir -p /etc/apt/preferences.d /etc/apt/sources.list.d # ensure directories exist
                    prep_create "/etc/apt/sources.list.d/linuxtoys-trixie-fuse.list" "/etc/apt/preferences.d/linuxtoys-trixie-fuse"
                    echo 'deb https://deb.debian.org/debian trixie main' | sudo_ tee /etc/apt/sources.list.d/linuxtoys-trixie-fuse.list >/dev/null
                    sudo_ tee /etc/apt/preferences.d/linuxtoys-trixie-fuse >/dev/null <<'EOF'
Package: *
Pin: release n=trixie
Pin-Priority: -1

Package: libfuse2t64
Pin: release n=trixie
Pin-Priority: 990
EOF
                fi
                pkg_install libfuse2t64;
            }
        fi
    }
    { is_fedora || is_ostree || is_rhel; } && {
        pkg_exists fuse
        [[ ! ${#pkg_notfound[@]} -eq 0 ]] && {
            pkg_install --ostreecheck fuse;
        }
    }
    { is_arch || is_cachy || is_solus; } && {
        pkg_exists fuse
        [[ ! ${#pkg_notfound[@]} -eq 0 ]] && {
            pkg_install fuse2;
        }
    }
    prep_dir "$HOME/AppImages"

    # Prefer Gear Lever on systemd systems. If it cannot inspect/integrate an
    # otherwise valid AppImage, fall back to LinuxToys' own simple integration.
    if is_systemd; then
        if ! flatpak list | grep -q "it.mijorus.gearlever"; then
            info "$gearlevermsg"
            call_script it.mijorus.gearlever
        fi
        local output
        if output=$(echo "y" | flatpak run it.mijorus.gearlever --integrate "$@" 2>&1); then
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
                warn "Could not determine integrated AppImage filename."
            fi
            return 0
        fi

        echo "$output"
        warn "Gear Lever integration failed. Falling back to LinuxToys AppImage integration."
    fi

    # Minimal fallback/non-systemd integration. Repository metadata already
    # supplies the application name, description and icon, so desktop_shortcut
    # can create a consistent launcher without extracting AppImage metadata.
    for appimage_file in "$@"; do
        [[ -f "$appimage_file" ]] || fatal "AppImage file not found: $appimage_file"

        local appimage_basename target_appimage
        appimage_basename="$(basename -- "$appimage_file")"
        target_appimage="$HOME/AppImages/$appimage_basename"

        prep_create "$target_appimage"
        cp -f -- "$appimage_file" "$target_appimage" || fatal "Failed to copy AppImage: $appimage_basename"
        chmod +x -- "$target_appimage" || fatal "Failed to make AppImage executable: $appimage_basename"

        # Keep the desktop launcher bound to the AppImage's absolute path, while
        # exposing a stable LinuxToys app-ID command through ~/.local/bin.
        path_link --useappid "$target_appimage"
        desktop_shortcut "\"$target_appimage\""
        _append_transmap "appimage $appimage_basename"
    done
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
            { npm install -g "${flags[@]}" "$pkg" 2>/dev/null || sudo_ npm install -g "${flags[@]}" "$pkg"; } || fatal "Failed to install npm package $pkg"
            _append_transmap "npm $pkg"
        fi
    done
}

pkg_bun () {
    if ! command -v bun &>/dev/null; then
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
