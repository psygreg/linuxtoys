# --- Miscellaneous ---

# shell change
shell_change() {
    sudo chsh -s "$*" || fatal "Failed to change shell: $*"
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
        askpass
        sudo -i sh -c "'flatpak override --$scope --$type=$setting $target'"
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

    local target="$1"
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
    local safe_id desktop_file executable wmclass

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

    safe_id=$(printf '%s' "$app_id" | tr -cs 'A-Za-z0-9._-' '-' | sed 's/^-*//; s/-*$//')
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
