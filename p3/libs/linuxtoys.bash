# --- LinuxToys Shell Library ---
# core modules automatically sourced

source "$SCRIPT_DIR/libs/sysinfo.bash"
[ -n "$FS_OPS" ] && source "$SCRIPT_DIR/libs/fsops.bash"
[ -n "$PACKAGE_OPS" ] && source "$SCRIPT_DIR/libs/packages.bash"
[ -n "$BOOT_OPS" ] && source "$SCRIPT_DIR/libs/boot.bash"
[ -n "$MISC_OPS" ] && source "$SCRIPT_DIR/libs/misc.bash"
{ is_systemd && [ -n "$SYSD_OPS" ]; } && source "$SCRIPT_DIR/libs/sysd.bash"

# sourcing
summon_helpers() {
    source "$SCRIPT_DIR/libs/helpers.lib" || fatal "Helpers library not found"
}
summon_optimizers() {
    source "$SCRIPT_DIR/libs/optimizers.lib" || fatal "Optimizers library not found"
}

# --- Zenity compatibility layer ---
_zenity_can_run() {
    [[ "$DISABLE_ZENITY" != "1" ]] || return 1
    type -P zenity >/dev/null 2>&1 || return 1
    [[ -n "$DISPLAY" || -n "$WAYLAND_DISPLAY" ]] || return 1
    return 0
}
_zenity_run() {
    _zenity_can_run || return 1
    GTK_A11Y=none NO_AT_BRIDGE=1 command zenity "$@" 2>/dev/null
}
# Wrapper for scripts that call zenity directly after sourcing this library.
zenity() {
    _zenity_run "$@"
}

# privilege escalation
askpass() {
    local mode="${1:-sudo}"
    shift || true

    local title="${1:-LinuxToys}"
    local _pass=""
    local max_attempts=3
    local attempts=0
    local marker="${TMPDIR:-/tmp}/linuxtoys_sudo_validated-${UID}"

    case "$mode" in
        password)
            # Explicit CLI mode.
            if [[ ${DISABLE_ZENITY:-0} == "1" ]]; then
                [[ -t 0 ]] || return 1

                read -rsp "Password: " _pass || return 1
                printf '\n' >&2
            else
                # GUI mode must use Zenity. Do not silently redirect password
                # input to the terminal viewer.
                _zenity_can_run || return 1

                _pass=$(
                    _zenity_run \
                        --password \
                        --title="$title"
                ) || return 1
            fi

            [[ -n "$_pass" ]] || return 1
            printf '%s' "$_pass"
            ;;

        sudo)
            # Only sudo itself can confirm whether the current authorization
            # is still valid. The marker must not bypass this check.
            if sudo -n true 2>/dev/null; then
                return 0
            fi

            # Remove a stale informational marker.
            rm -f "$marker"

            if [[ ${DISABLE_ZENITY:-0} == "1" ]]; then
                while (( attempts < max_attempts )); do
                    _pass=$(askpass password "$title") || return 1

                    if printf '%s\n' "$_pass" |
                        sudo -S -p '' -v >/dev/null 2>&1; then
                        unset _pass

                        if [[ -n ${LINUXTOYS_CHECKLIST:-} ]]; then
                            touch "$marker"
                        fi

                        return 0
                    fi

                    unset _pass
                    ((attempts++))

                    printf '❌ Wrong password. Attempts: %d/%d.\n' \
                        "$attempts" "$max_attempts" >&2
                done

                _msg error \
                    "❌ Wrong password or sudo failed (max attempts reached)." \
                    "Authentication Failed"
                exit 100
            fi

            _pass=$(askpass password "$title") || {
                _msg error \
                    "Password dialog cancelled or could not be displayed." \
                    "Authentication Failed"
                exit 100
            }

            if command -v sudo-rs >/dev/null 2>&1; then
                if ! printf '%s\n' "$_pass" |
                    sudo-rs -Sv >/dev/null 2>&1; then
                    unset _pass

                    _msg error \
                        "Wrong password or authentication failed." \
                        "Authentication Failed"
                    exit 100
                fi
            else
                if ! printf '%s\n' "$_pass" |
                    sudo -S -p '' -v >/dev/null 2>&1; then
                    unset _pass

                    _msg error \
                        "Wrong password or authentication failed." \
                        "Authentication Failed"
                    exit 100
                fi
            fi

            unset _pass

            if [[ -n ${LINUXTOYS_CHECKLIST:-} ]]; then
                touch "$marker"
            fi

            return 0
            ;;

        *)
            printf 'askpass: unknown mode: %s\n' "$mode" >&2
            return 2
            ;;
    esac
}

# Unified message handler
_msg() {
    local type="$1"
    local text="$2"
    local title="${3:-LinuxToys}"

    if [[ "$DISABLE_ZENITY" == "1" ]]; then
        echo "$text"
        return 0
    fi

    case "$type" in
        info)
            _zenity_run --info --text "$text" --width 360 --height 300 || echo "$text"
            ;;
        warning)
            _zenity_run --warning --text "$text" --width 360 --height 300 || echo "$text"
            ;;
        error)
            echo "$text"
            _zenity_run --error --title "$title" --text "$text" --width 360 --height 300 || true
            ;;
        *)       echo "$text" ;;
    esac
}

# message presets
question() {
    local title="$1"
    local text="$2"
    local width="${3:-360}"
    local height="${4:-300}"
    if [[ "$DISABLE_ZENITY" == "1" ]]; then
        return 0
    fi
    if _zenity_run --question --title "$title" --text "$text" --width "$width" --height "$height"; then
        return 0
    fi
    if [[ -t 0 ]]; then
        local _reply
        read -r -p "$text [y/N] " _reply
        [[ "$_reply" =~ ^[Yy]$ ]]
        return $?
    fi
    return 1
}
info() { 
    { { [ -n "$CALLED_SCRIPT" ] && { [ "$1" = "$finishmsg" ] || [ "$1" = "$rebootmsg" ]; }; } && return 0; } || true
    _zenity_can_run || { echo "$1" && return 0; }
    if [ -n "$CHECKLIST_RUN" ]; then
        echo "$1"; 
    else
        _msg info "$1";
    fi
}
warn() { 
    _zenity_can_run || { echo "$1" && return 0; }
    if [ -n "$CHECKLIST_RUN" ]; then
        echo "WARN: $1"; 
    else
        _msg warning "$1";
    fi
}
error() {
    _zenity_can_run || { echo "$1" && return 1; }
    _msg error "$1" "Error"
    return 1
}
die() {
    _zenity_can_run || { echo "$1" && exit 1; }
    _msg error "$1" "Fatal Error"
    exit 1
}

# legacy function calls
zenpass() { askpass password "$@"; }
sudo_rq() { askpass sudo "$@"; }
zenask() { question "$@"; }
zenwrn() { warn "$@"; }
zeninf() { info "$@"; }
nonfatal() { error "$@"; }
fatal() { die "$@"; }

# --- Utils ---
_lang_() {
    local lang="${LANG:0:2}"
    local available=" am ar bn cs de el en es fa fi fr he hi id it ja ko ms nl pl pt ru sv sw ta th tl tr uk ur vi zh bg bs da hr hu is no sk sl sr nb az lv ga ne my sq tg uz hy ka km lo mn ro et lt "

    if [[ "$available" == *" $lang "* ]]; then
        langfile="$lang"
    else
        langfile="en"
    fi
    source "$SCRIPT_DIR/libs/lang/$langfile.lib"
}
_lang_

# transaction map control
init_transmap() {
    [ -n "$TRANSMAP_PATH" ] && return 0
    TRANSMAP_CALL="1" && prep_tmp
    unset TRANSMAP_CALL
    { [ -d "$TEMPDIR" ] && { 
        { [ -n "$TRANSMAP_PATH" ] || TRANSMAP_PATH="$TEMPDIR/transmap"; }
        { [ -f "$TRANSMAP_PATH" ] || { : > "$TRANSMAP_PATH" && chmod 600 "$TRANSMAP_PATH"; } }
    } } || die "Failed to create transaction map"
}
_append_transmap() {
    init_transmap
    echo "$1" >> "$TRANSMAP_PATH" 2>/dev/null
}

# script calling -- used for scripts to call other scripts from the app.
call_script () {
    local script_name="$1"
    [[ -z "$script_name" ]] && die "call_script: script name not provided"
    [[ -z "$CACHE_DIR" ]] && die "call_script: CACHE_DIR environment variable not set"

    script_name="${script_name%.sh}"
    local script_file="${script_name}.sh"

    local found_script
    found_script=$(find "$CACHE_DIR" -maxdepth 3 -type f \
        -name "$script_file" 2>/dev/null | head -n1)

    [[ -n "$found_script" && -f "$found_script" ]] ||
        die "call_script: Script '$script_name' not found in $CACHE_DIR"
    python3 "$SCRIPT_DIR/app/compat.py" --check-script "$found_script" || { 
        echo "W: call_script: Script '$script_name' is not compatible with this host, skipping."
        return 2
    }

    shift
    # Get the script's registry/display name.
    local script_display_name
    script_display_name=$(
        sed -n 's/^# name:[[:space:]]*//p' "$found_script" |
        head -n1
    )
    [[ -n "$script_display_name" ]] ||
        script_display_name="$script_name"

    # Keep track of the caller's transaction.
    local parent_transmap="$TRANSMAP_PATH"

    # Create an independent transaction for the called script.
    local child_transmap
    child_transmap=$(mktemp "/tmp/linuxtoys-called-XXXXXX.transmap") ||
        die "call_script: Failed to create child transmap"

    (
        export CALLED_SCRIPT=1
        export TRANSMAP_PATH="$child_transmap"

        python3 "$SCRIPT_DIR/app/library_loader.py" "$found_script" "$@"
    )
    local status=$?

    if [[ $status -eq 0 ]]; then
        # Commit the called script's transaction independently.
        if [[ -s "$child_transmap" ]]; then
            python3 "$SCRIPT_DIR/app/term_registry.py" \
                save "$script_display_name" "$child_transmap" ||
                die "Failed to save transaction for $script_display_name"
            _append_transmap "called $script_display_name"
        fi
        rm -f "$child_transmap"
        return 0
    fi

    # Failed child: merge its changes into the caller's transaction,
    # allowing the normal top-level auto-revert to undo them.
    if [[ -s "$child_transmap" ]]; then
        if [[ -n "$parent_transmap" ]]; then
            cat "$child_transmap" >> "$parent_transmap"
        else
            init_transmap
            cat "$child_transmap" >> "$TRANSMAP_PATH"
        fi
    fi

    rm -f "$child_transmap"
    return "$status"
}

run_list_hook() {
    local hook="$1"
    local path=""

    if [ -n "${CACHE_DIR:-}" ] &&
       [ -f "$CACHE_DIR/scripts/lists/$hook" ]; then
        path="$CACHE_DIR/scripts/lists/$hook"
    elif [ -f "$SCRIPT_DIR/scripts/lists/$hook" ]; then
        path="$SCRIPT_DIR/scripts/lists/$hook"
    else
        die "Repository hook script not found: $hook"
    fi

    source "$path"
}