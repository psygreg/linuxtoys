# --- Miscellaneous ---

# shell change
shell_change() {
    sudo_ chsh -s "$*" || fatal "Failed to change shell: $*"
    _append_transmap "chsh $*"
}

# distrobox container
distrobox_created() {
    _append_transmap "distrobox $*"
}

# rclone mountpoint
rclone_mount() {
    local remote="$1"
    local mount_point="$2"
    if [[ "$remote" != *:* ]]; then
        remote="${remote}:"
    fi
    rclone mount "$remote" "$mount_point" --daemon || fatal "Failed to create rclone mountpoint"
    _append_transmap "rclone mounted $remote at $mount_point"
}

# swapfile creation
swapfile_created () {
    _append_transmap "swapfile $*"
}

# Mounted storage units beyond the OS-critical mounts: filesystems backed by
# real block devices, excluding squashfs images and the root/home/boot/EFI
# mounts. Optional arguments are extra mount trees to exclude (prefix match).
# Prints one decoded mount point per line.
list_storage_drives() {
    local -a excludes=("/" "/home" "/boot")
    local -a efi_prefixes=("/boot/efi" "/efi")
    local target source fstype exclude skip

    while read -r target source fstype; do
        [[ "$target" == /* ]] || continue
        [[ "$source" == /dev/* ]] || continue
        [[ "$fstype" == "squashfs" ]] && continue

        # findmnt --raw hex-escapes unsafe characters (spaces, backslashes).
        target="$(printf '%b' "$target")"

        skip=0
        for exclude in "${excludes[@]}"; do
            [[ "$target" == "$exclude" ]] && { skip=1; break; }
        done
        (( skip )) && continue
        for exclude in "${efi_prefixes[@]}" "$@"; do
            [[ "$target" == "$exclude" || "$target" == "$exclude/"* ]] && { skip=1; break; }
        done
        (( skip )) && continue

        printf '%s\n' "$target"
    done < <(findmnt -rn --raw -o TARGET,SOURCE,FSTYPE)
}

# check if sufficient disk space is available for a DaVinci Resolve install
check_disk_space () {
    local pkgname="$1"
    local required_space_gb=0

    # set required space based on package type
    if [ "$pkgname" == "davinci-resolve" ]; then
        required_space_gb=15
    elif [ "$pkgname" == "davinci-resolve-studio" ]; then
        required_space_gb=30
    fi

    local required_space_kb=$((required_space_gb * 1024 * 1024))

    # On immutable OSes using composeFS (and similar), / is a tiny read-only
    # mount with no usable space; the writable root lives at /var. Detect this
    # and check /var instead of / as the 'root' partition.
    local root_path="/"
    if [ -d /var ] && { [ -f /run/ostree-booted ] || findmnt -n -o FSTYPE --target / 2>/dev/null | grep -qiE 'composefs|erofs|overlay'; }; then
        root_path="/var"
    fi

    # --output=avail keeps the unit and the column layout stable regardless
    # of DF_BLOCK_SIZE or POSIXLY_CORRECT, unlike parsing plain df.
    local home_available_kb root_available_kb
    home_available_kb=$(df --output=avail -k "$HOME" 2>/dev/null | tail -n 1 | tr -d ' ')
    root_available_kb=$(df --output=avail -k "$root_path" 2>/dev/null | tail -n 1 | tr -d ' ')

    # An unmeasurable filesystem must not pass the check silently: the tests
    # below error out on an empty value and are then treated as false. Warn
    # and skip only that path; later writes still fail loudly on their own.
    if ! [[ "$home_available_kb" =~ ^[0-9]+$ ]]; then
        warn "Could not determine available storage space on $HOME; skipping that check."
        home_available_kb=""
    fi
    if ! [[ "$root_available_kb" =~ ^[0-9]+$ ]]; then
        warn "Could not determine available storage space on $root_path; skipping that check."
        root_available_kb=""
    fi

    # check home directory
    if [ -n "$home_available_kb" ] && [ "$home_available_kb" -lt "$required_space_kb" ]; then
        fatal "$outofspace\n$HOME -- $required_space_gb GB (found $home_available_kb KB free)"
    fi

    # check root filesystem
    if [ -n "$root_available_kb" ] && [ "$root_available_kb" -lt "$required_space_kb" ]; then
        fatal "$outofspace\n$root_path 'root' -- $required_space_gb GB (found $root_available_kb KB free)"
    fi
}

# flatpak overrides
flatpak_override () {
    local scope pretype type setting target
    scope="$1"
    pretype="$2"
    setting="$3"
    target="$4"

    case "$pretype" in
        fs) type="filesystem" ;;
        name) type="talk-name" ;;
        dbus) type="talk-dbus" ;;
        share|env|runtime|device|socket|filesystem|talk-name|talk-dbus) type="$pretype" ;;
        *) die "Invalid override type" ;;
    esac

    flatpak info "$target" &>/dev/null || { echo "W: override target not available" && return 100; }

    if [ "$scope" = "system" ]; then
        # Direct call: `sudo_ -i sh -c` cannot be used here because sudo_ prepends
        # `env DBUS_SESSION_BUS_ADDRESS=...` when forwarding the desktop session
        # bus, and env would treat the trailing `-i` as the command to execute.
        sudo_ flatpak override --"$scope" --"$type"="$setting" "$target"
    elif [ "$scope" = "user" ]; then
        flatpak override --"$scope" --"$type"="$setting" "$target"
    else
        die "Invalid override scope"
    fi

    _append_transmap "override $scope $type $setting $target"
}

# user PATH executable link
path_link() {
    local use_appid=0
    local target=""
    local arg

    for arg in "$@"; do
        case "$arg" in
            --useappid)
                use_appid=1
                ;;
            --*)
                die "path_link: unknown option: $arg"
                ;;
            *)
                [ -z "$target" ] || die "path_link: expects exactly one executable"
                target="$arg"
                ;;
        esac
    done

    local bin_dir="$HOME/.local/bin"
    local link_name link_path resolved_target

    [ -n "$target" ] || die "path_link received an empty target"
    [ -e "$target" ] || die "path_link target does not exist: $target"
    [ -f "$target" ] || die "path_link target is not a file: $target"

    resolved_target=$(readlink -f -- "$target") || die "Failed to resolve path_link target: $target"

    if [ "$use_appid" -eq 1 ]; then
        [ -n "${LINUXTOYS_APP_ID:-}" ] || die "path_link --useappid: LinuxToys app identity is unavailable"
        link_name="${LINUXTOYS_APP_ID,,}"
        link_name="${link_name//_/-}"
    else
        link_name="${resolved_target##*/}"
    fi
    [ -n "$link_name" ] || die "Could not derive executable name from: $target"

    mkdir -p "$bin_dir"

    # Make the conventional per-user binary directory available immediately and
    # persist it for future sessions without replacing the user's existing PATH.
    case ":${PATH:-}:" in
        *":$bin_dir:"*) ;;
        *) export PATH="$bin_dir${PATH:+:$PATH}" ;;
    esac

    local path_line='case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH" ;; esac'
    local shell_name="${SHELL##*/}"
    local -a path_configs=("$HOME/.profile")

    # Also update the active shell's interactive startup file so new terminals
    # inherit the path even before the next graphical/login session.
    case "$shell_name" in
        bash) path_configs+=("$HOME/.bashrc") ;;
        zsh)  path_configs+=("$HOME/.zshrc") ;;
    esac

    local config
    for config in "${path_configs[@]}"; do
        if [ -f "$config" ] && grep -Eq '(^|[^[:alnum:]_])(~|\$\{?HOME\}?)/\.local/bin([^[:alnum:]_]|$)' "$config" 2>/dev/null; then
            continue
        fi
        prep_edit "$config"
        printf '%s\n' "$path_line" >> "$config" || die "Failed to add ~/.local/bin to PATH in: $config"
    done

    # Fish uses its own syntax and supports drop-in startup snippets natively.
    if [ "$shell_name" = "fish" ] || [ -d "$HOME/.config/fish" ]; then
        local fish_conf="$HOME/.config/fish/conf.d/linuxtoys-path.fish"
        mkdir -p "${fish_conf%/*}"
        if [ ! -f "$fish_conf" ] || ! grep -Fq '$HOME/.local/bin' "$fish_conf"; then
            prep_edit "$fish_conf"
            printf '%s\n' 'fish_add_path -g "$HOME/.local/bin"' > "$fish_conf" || die "Failed to add ~/.local/bin to Fish PATH"
        fi
    fi

    link_path="$bin_dir/$link_name"

    # Idempotent when the requested link is already correct.
    if [ -L "$link_path" ] && [ "$(readlink -f -- "$link_path" 2>/dev/null)" = "$resolved_target" ]; then
        return 0
    fi

    # Do not silently replace an unrelated user command.
    if [ -e "$link_path" ] || [ -L "$link_path" ]; then
        die "PATH entry already exists and points elsewhere: $link_path"
    fi

    ln -s -- "$resolved_target" "$link_path" || die "Failed to link executable into PATH: $link_path"
    _append_transmap "created $link_path"
}

# desktop application shortcut
desktop_shortcut() {
    local wmclass_override=""

    if [ "${1:-}" = "--class" ]; then
        [ "$#" -eq 3 ] || die "desktop_shortcut --class expects a WM class and one Exec value"
        wmclass_override="$2"
        shift 2
    else
        [ "$#" -eq 1 ] || die "desktop_shortcut expects exactly one Exec value"
    fi

    local exec_line="$1"
    local app_id="${LINUXTOYS_APP_ID:-}"
    local app_name="${LINUXTOYS_APP_NAME:-}"
    local app_description="${LINUXTOYS_APP_DESCRIPTION:-}"
    local app_icon="${LINUXTOYS_APP_ICON:-}"
    local applications_dir="$HOME/.local/share/applications"
    local safe_id desktop_file executable wmclass existing_desktop

    [ -n "$exec_line" ] || die "desktop_shortcut received an empty Exec value"
    [ -n "$app_id" ] || die "LinuxToys app identity is unavailable"
    [ -n "$app_name" ] || die "LinuxToys app name is unavailable"
    [ -n "$app_icon" ] || app_icon="application-x-executable"

    # Desktop entries cannot contain literal line breaks in these scalar fields.
    app_name="${app_name//$'\r'/ }"
    app_name="${app_name//$'\n'/ }"
    app_description="${app_description//$'\r'/ }"
    app_description="${app_description//$'\n'/ }"
    app_icon="${app_icon//$'\r'/}"
    app_icon="${app_icon//$'\n'/}"
    exec_line="${exec_line//$'\r'/}"
    exec_line="${exec_line//$'\n'/ }"
    wmclass_override="${wmclass_override//$'\r'/}"
    wmclass_override="${wmclass_override//$'\n'/ }"

    if [ -d "$applications_dir" ]; then
        for existing_desktop in "$applications_dir"/*.desktop; do
            [ -f "$existing_desktop" ] || continue

            if grep -Fxq "Name=$app_name" "$existing_desktop" \
                && grep -Fxq "Exec=$exec_line" "$existing_desktop"; then
                echo "Desktop shortcut already exists: $existing_desktop"
                return 0
            fi
        done
    fi

    safe_id=$(printf '%s' "${app_id,,}" | tr -cs 'a-z0-9._-' '-' | sed 's/^-*//; s/-*$//')
    [ -n "$safe_id" ] || safe_id="application"
    desktop_file="$HOME/.local/share/applications/linuxtoys-${safe_id}.desktop"

    # Persist icons that live inside the temporary AppImage mount.
    if [ "${LINUXTOYS_APPIMAGE:-0}" = "1" ] \
        && [ -n "${LINUXTOYS_APPIMAGE_DIR:-}" ] \
        && [ -f "$app_icon" ]; then

        case "$app_icon" in
            "$LINUXTOYS_APPIMAGE_DIR"/*)
                local icon_dir icon_name persistent_icon

                if [ -n "${LINUXTOYS_TARBALL_DIR:-}" ]; then
                    icon_dir="$LINUXTOYS_TARBALL_DIR"
                elif [ -n "${LINUXTOYS_BIN_DIR:-}" ]; then
                    icon_dir="$LINUXTOYS_BIN_DIR"
                else
                    icon_dir="$HOME/.local/share/linuxtoys/icons/$safe_id"
                    mkdir -p "$icon_dir" || die "Failed to create persistent icon directory: $icon_dir"
                fi

                icon_name="${app_icon##*/}"
                persistent_icon="$icon_dir/$icon_name"

                if [ "$app_icon" != "$persistent_icon" ]; then
                    cp -f -- "$app_icon" "$persistent_icon" || die "Failed to persist application icon: $app_icon"
                fi

                app_icon="$persistent_icon"
                ;;
        esac
    fi

    if [ -n "$wmclass_override" ]; then
        wmclass="$wmclass_override"
    else
        # StartupWMClass normally follows the executable basename. Support both an
        # unquoted executable and a quoted executable followed by arguments.
        case "$exec_line" in
            \"*\") executable="${exec_line#\"}"; executable="${executable%%\"*}" ;;
            \'*\') executable="${exec_line#\'}"; executable="${executable%%\'*}" ;;
            *) executable="${exec_line%%[[:space:]]*}" ;;
        esac
        wmclass="${executable##*/}"
        [ -n "$wmclass" ] || die "Could not derive StartupWMClass from Exec value"
    fi

    prep_create "$desktop_file"

    {
        printf '%s\n' '[Desktop Entry]'
        printf 'Type=Application\n'
        printf 'Name=%s\n' "$app_name"
        [ -z "$app_description" ] || printf 'Comment=%s\n' "$app_description"
        printf 'Exec=%s\n' "$exec_line"
        printf 'Icon=%s\n' "$app_icon"
        printf 'Terminal=false\n'
        printf 'StartupNotify=true\n'
        printf 'StartupWMClass=%s\n' "$wmclass"
    } > "$desktop_file" || die "Failed to write desktop shortcut: $desktop_file"

    chmod 0644 "$desktop_file" || die "Failed to set permissions on desktop shortcut"

    if command -v desktop-file-validate >/dev/null 2>&1; then
        desktop-file-validate "$desktop_file" || die "Generated desktop shortcut is invalid"
    fi

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true
    fi
}

# Return 0 when a no-longer-recorded absolute path still has a live AppImage
# sibling in the same directory. AppImage integration flows (Gear Lever, the
# ArtCraft Launcher, ...) place the AppImage under a version-suffixed filename
# (photocraft-0.20.1-linux-x86_64.AppImage) and replace it with the next one
# (photocraft-0.20.2-linux-x86_64.AppImage) on update, sometimes without
# rewriting the desktop entry's Exec/TryExec in step. The app is then still
# installed and launchable, just under the new name: treating the stale
# version-suffixed path as a dead target would erase a working app's menu
# shortcut. Only treat the target as still installed when another .AppImage
# file with the same app stem (basename up to the first hyphen,
# case-insensitively, so artcraft_launcher.appimage matches itself but
# photograd-1.0.0.AppImage does not shadow photocraft) exists beside it.
# Every other missing target keeps the plain missing-file verdict.
_appimage_sibling_present () {
    local target case_name dir stem candidate found=0
    target="$1"

    case_name="${target##*/}"
    [[ "$case_name" =~ \.[Aa]pp[Ii]mage$ ]] || return 1

    dir="${target%/*}"
    [[ -d "$dir" ]] || return 1

    stem="${case_name%%-*}"
    [[ -n "$stem" ]] || return 1

    shopt -s nullglob nocaseglob
    for candidate in "$dir"/*.appimage; do
        if [[ ${candidate##*/} == "$stem"* ]]; then
            found=1
            break
        fi
    done
    shopt -u nullglob nocaseglob

    if [[ "$found" == 1 ]]; then
        return 0
    fi

    return 1
}

# Return 0 when a user .desktop launcher no longer points at an installed app.
# Conservative: only Flatpak/Snap/TryExec/absolute-Exec orphans are removed;
# complex wrappers (env/sh -c/wine) are left alone.
_desktop_launcher_is_orphan() {
    local desktop_file="$1"
    local entry_type="" try_exec="" exec_line="" cmd="" app_id="" snap_name=""

    # Flatpak export symlinks that lost their target leave broken menu entries.
    if [[ -L "$desktop_file" && ! -e "$desktop_file" ]]; then
        return 0
    fi
    [[ -f "$desktop_file" ]] || return 1

    while IFS= read -r line || [[ -n "$line" ]]; do
        case "$line" in
            '[Desktop Entry]')
                entry_type="Application"
                try_exec=""
                exec_line=""
                ;;
            \[*)
                break
                ;;
            Type=*)
                entry_type="${line#Type=}"
                ;;
            TryExec=*)
                try_exec="${line#TryExec=}"
                ;;
            Exec=*)
                [[ -n "$exec_line" ]] || exec_line="${line#Exec=}"
                ;;
        esac
    done < "$desktop_file"

    [[ -z "$entry_type" || "$entry_type" == "Application" ]] || return 1

    if [[ -n "$try_exec" ]]; then
        if [[ "$try_exec" == /* ]]; then
            [[ -e "$try_exec" ]] || _appimage_sibling_present "$try_exec" || return 0
        else
            command -v -- "$try_exec" >/dev/null 2>&1 || return 0
        fi
    fi

    [[ -n "$exec_line" ]] || return 1
    # Desktop Entry field codes are not part of the command.
    exec_line="${exec_line//%%/ }"
    exec_line=$(printf '%s' "$exec_line" | sed -E 's/%[fFuUdDnNickvm]//g')

    # Flatpak launchers survive uninstall when copied into ~/.local/share/applications.
    if [[ "$exec_line" == *flatpak*run* ]]; then
        app_id=$(printf '%s\n' "$exec_line" | grep -oE '[A-Za-z0-9_]+\.[A-Za-z0-9_]+(\.[A-Za-z0-9_]+)+' | tail -n1)
        if [[ -n "$app_id" ]]; then
            if command -v flatpak >/dev/null 2>&1; then
                flatpak info "$app_id" >/dev/null 2>&1 || return 0
            else
                return 0
            fi
        fi
    elif [[ "$exec_line" == */var/lib/flatpak/* || "$exec_line" == */.local/share/flatpak/* ]]; then
        cmd="${exec_line%%[[:space:]]*}"
        cmd="${cmd#\"}"
        cmd="${cmd%\"}"
        [[ -e "$cmd" ]] || return 0
    fi

    # Snap launchers left behind after snap remove.
    if [[ "$exec_line" =~ snap[[:space:]]+run[[:space:]]+([^[:space:]]+) ]]; then
        snap_name="${BASH_REMATCH[1]}"
        snap_name="${snap_name%%.*}"
        if command -v snap >/dev/null 2>&1; then
            snap list "$snap_name" >/dev/null 2>&1 || return 0
        else
            return 0
        fi
    elif [[ "$exec_line" =~ /snap/bin/([^[:space:]\"]+) ]]; then
        snap_name="${BASH_REMATCH[1]}"
        snap_name="${snap_name%%.*}"
        if command -v snap >/dev/null 2>&1; then
            snap list "$snap_name" >/dev/null 2>&1 || return 0
        else
            [[ -e "/snap/bin/${BASH_REMATCH[1]}" ]] || return 0
        fi
    fi

    # Absolute Exec targets (AUR copies, AppImages, hand-made shortcuts).
    # Skip wrappers we cannot validate safely.
    case "$exec_line" in
        env\ *|sh\ *|bash\ *|\"env\ *|\'env\ *|\"sh\ *|\'sh\ *|\"bash\ *|\'bash\ *)
            return 1
            ;;
    esac
    if [[ "$exec_line" == \"* ]]; then
        cmd="${exec_line#\"}"
        cmd="${cmd%%\"*}"
    elif [[ "$exec_line" == \'* ]]; then
        cmd="${exec_line#\'}"
        cmd="${cmd%%\'*}"
    else
        cmd="${exec_line%%[[:space:]]*}"
    fi
    if [[ "$cmd" == /* ]]; then
        [[ -e "$cmd" ]] || _appimage_sibling_present "$cmd" || return 0
    fi

    return 1
}

# Drop leftover user menu shortcuts whose Flatpak/Snap/native targets are gone.
# AppImage targets whose version-suffixed filename was replaced on update are
# not orphans: a sibling .AppImage with the same app stem keeps the entry.
# Safe for sysup: never fatal, never touches system-wide application dirs, and
# skips root service runs (those have no user menu worth cleaning).
cleanup_orphan_desktops() {
    [ "$(id -u)" -ne 0 ] || return 0

    local applications_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    [[ -d "$applications_dir" ]] || return 0

    local desktop_file removed=0
    shopt -s nullglob
    for desktop_file in "$applications_dir"/*.desktop; do
        _desktop_launcher_is_orphan "$desktop_file" || continue
        rm -f -- "$desktop_file" 2>/dev/null || {
            warn "Failed to remove orphaned desktop shortcut: $desktop_file"
            continue
        }
        echo "Removed orphaned desktop shortcut: ${desktop_file##*/}"
        removed=$((removed + 1))
    done
    shopt -u nullglob

    if (( removed > 0 )) && command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database "$applications_dir" >/dev/null 2>&1 || true
    fi
    return 0
}
