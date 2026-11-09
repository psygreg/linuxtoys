# --- LinuxToys Shell Library ---
# core modules automatically sourced

source "$SCRIPT_DIR/libs/sysinfo.bash"
source "$SCRIPT_DIR/libs/timefix.bash"
[ -n "$FS_OPS" ] && source "$SCRIPT_DIR/libs/fsops.bash"
[ -n "$PACKAGE_OPS" ] && source "$SCRIPT_DIR/libs/packages.bash"
[ -n "$BOOT_OPS" ] && source "$SCRIPT_DIR/libs/boot.bash"
[ -n "$MISC_OPS" ] && source "$SCRIPT_DIR/libs/misc.bash"
{ is_systemd && [ -n "$SYSD_OPS" ]; } && source "$SCRIPT_DIR/libs/sysd.bash"
[ -n "$HELPERS_OPS" ] && source "$SCRIPT_DIR/libs/helpers.bash"
[ -n "$OPTIMIZER_OPS" ] && source "$SCRIPT_DIR/libs/optimizers.bash"

# GLib/libdbus clients (flatpak, gsettings, ...) connect to the session bus at
# startup; without an address they fall back to autolaunching dbus-launch,
# which is absent on stock GNOME installs and fails elsewhere. Launch contexts
# that strip the desktop environment (TTY, cron, systemd units) still have the
# per-user bus socket, so derive the address when it is missing.
if [[ -z "${DBUS_SESSION_BUS_ADDRESS:-}" && -S "/run/user/${UID}/bus" ]]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/${UID}/bus"
fi

# legacy explicit sourcing
summon_helpers() {
    [ -n "$HELPERS_OPS" ] && return 0
    source "$SCRIPT_DIR/libs/helpers.lib" || fatal "Helpers library not found"
}
summon_optimizers() {
    [ -n "$OPTIMIZER_OPS" ] && return 0
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

    local status
    GTK_A11Y=none \
    NO_AT_BRIDGE=1 \
    G_DEBUG="" \
    command zenity "$@" 2>/dev/null
    status=$?

    # Expected statuses:
    #   0   = accepted/success
    #   1   = cancelled/closed
    #   100 = LinuxToys cancellation
    # Anything else above 1 indicates an abnormal failure.
    if (( status > 1 && status != 100 )); then
        printf 'W: zenity exited abnormally (status %d).\n' "$status" >&2
    fi
    return "$status"
}
# Wrapper for scripts that call zenity directly after sourcing this library.
zenity() {
    local -a _zargs=()
    local _arg _val _prev=""
    for _arg in "$@"; do
        case "$_arg" in
            --text=*)
                _val="${_arg#--text=}"
                _zargs+=("--text=$(_msg_unescape "$_val")")
                ;;
            --text)
                _zargs+=("--text")
                ;;
            *)
                if [ "$_prev" = "--text" ]; then
                    _zargs+=("$(_msg_unescape "$_arg")")
                else
                    _zargs+=("$_arg")
                fi
                ;;
        esac
        _prev="$_arg"
    done
    _zenity_run "${_zargs[@]}"
}

# privilege escalation
_sudo_command_path() {
    local sudo_path run0_path

    sudo_path=$(type -P sudo 2>/dev/null) || sudo_path=""
    run0_path=$(type -P run0-sudo 2>/dev/null) || run0_path=""

    # run0-wrappers commonly installs `sudo` as a symlink to run0-sudo. Use the
    # run0 backend when that is the implementation behind `sudo`, or when it
    # is the only available sudo-compatible command.
    if [[ -n "$run0_path" ]] && {
        [[ -z "$sudo_path" ]] || [[ "$sudo_path" -ef "$run0_path" ]]
    }; then
        printf '%s\n' "$run0_path"
    elif [[ -n "$sudo_path" ]]; then
        printf '%s\n' "$sudo_path"
    else
        return 127
    fi
}

_sudo_uses_run0_sudo() {
    local sudo_path="${1:-}" run0_path

    [[ -n "$sudo_path" ]] || return 1
    run0_path=$(type -P run0-sudo 2>/dev/null) || return 1
    [[ "$sudo_path" -ef "$run0_path" ]]
}

askpass() {
    local mode="${1:-sudo}"
    shift || true

    local title="LinuxToys"
    [[ "$mode" == "command" ]] || title="${1:-LinuxToys}"
    local _pass=""
    local sudo_cmd=""
    local sudo_shim_dir=""
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
            sudo_cmd=$(_sudo_command_path) || {
                printf 'askpass: no sudo or run0-sudo command found\n' >&2
                return 127
            }

            # Only the active privilege helper can confirm whether the current
            # authorization is still valid. The marker must not bypass this check.
            if "$sudo_cmd" -n true 2>/dev/null; then
                timefix_afterauth || true
                return 0
            fi

            # Remove a stale informational marker.
            rm -f "$marker"

            # run0-sudo delegates authentication to polkit; it does not accept
            # sudo's password-on-stdin options. Let the polkit agent handle the
            # prompt instead of opening LinuxToys' password dialog.
            if _sudo_uses_run0_sudo "$sudo_cmd"; then
                if ! "$sudo_cmd" -v; then
                    _msg error \
                        "Authorization failed or was cancelled." \
                        "Authentication Failed"
                    exit 100
                fi

                if [[ -n ${LINUXTOYS_CHECKLIST:-} ]]; then
                    touch "$marker"
                fi

                timefix_afterauth || true

                return 0
            fi

            if [[ ${DISABLE_ZENITY:-0} == "1" ]]; then
                while (( attempts < max_attempts )); do
                    _pass=$(askpass password "$title") || return 1

                    if printf '%s\n' "$_pass" |
                        "$sudo_cmd" -S -p '' -v >/dev/null 2>&1; then
                        unset _pass

                        if [[ -n ${LINUXTOYS_CHECKLIST:-} ]]; then
                            touch "$marker"
                        fi

                        timefix_afterauth || true

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
                    "$sudo_cmd" -S -p '' -v >/dev/null 2>&1; then
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

            timefix_afterauth || true

            return 0
            ;;

        command)
            sudo_cmd=$(_sudo_command_path) || sudo_cmd=""

            # run0-sudo authenticates through polkit, so don't collect a
            # password that it cannot consume via SUDO_ASKPASS. Put a sudo
            # symlink first in PATH so nested commands use the same backend.
            if [[ -n "$sudo_cmd" ]] && _sudo_uses_run0_sudo "$sudo_cmd"; then
                [[ "$sudo_cmd" == /* ]] || sudo_cmd="$PWD/$sudo_cmd"

                (
                    (( $# > 0 )) || {
                        printf 'askpass command: command not provided\n' >&2
                        exit 2
                    }
                    local command_status

                    sudo_shim_dir=$(mktemp -d "${TMPDIR:-/tmp}/linuxtoys-run0.XXXXXX") || exit 1
                    trap 'rm -rf -- "$sudo_shim_dir"' EXIT
                    trap 'exit 129' HUP
                    trap 'exit 130' INT
                    trap 'exit 143' TERM
                    chmod 700 "$sudo_shim_dir" || exit 1
                    ln -s -- "$sudo_cmd" "$sudo_shim_dir/sudo" || exit 1
                    unset SUDO_ASKPASS

                    if ! "$sudo_cmd" -v; then
                        _msg error \
                            "Authorization failed or was cancelled." \
                            "Authentication Failed"
                        exit 100
                    fi

                    if PATH="$sudo_shim_dir${PATH:+:$PATH}" "$@"; then
                        command_status=0
                    else
                        command_status=$?
                    fi
                    exit "$command_status"
                )
                return $?
            fi

            # Isolate helper state and traps from the calling script.
            (
                (( $# > 0 )) || {
                    printf 'askpass command: command not provided\n' >&2
                    exit 2
                }
                local askpass_dir askpass_fifo askpass_request askpass_helper feeder_pid=""
                local command_status
                askpass_dir=$(mktemp -d "${TMPDIR:-/tmp}/linuxtoys-askpass.XXXXXX") || exit 1
                trap '
                    if [[ -n "$feeder_pid" ]]; then
                        kill "$feeder_pid" 2>/dev/null || true
                        wait "$feeder_pid" 2>/dev/null || true
                    fi
                    unset _pass
                    rm -rf -- "$askpass_dir"
                ' EXIT
                trap 'exit 129' HUP
                trap 'exit 130' INT
                trap 'exit 143' TERM

                _pass=$(askpass password "$title") || exit 1
                chmod 700 "$askpass_dir" || exit 1
                askpass_fifo="$askpass_dir/password"
                askpass_request="$askpass_dir/request"
                askpass_helper="$askpass_dir/askpass"
                mkfifo -m 600 "$askpass_fifo" "$askpass_request" || exit 1
                # Quote the FIFO path as Bash syntax, including unusual TMPDIRs.
                {
                    printf '#!/usr/bin/env bash\n'
                    printf 'printf '\''request\n'\'' > %q || exit 1\n' "$askpass_request"
                    printf 'IFS= read -r password < %q || exit 1\n' "$askpass_fifo"
                    printf 'printf '\''%%s\n'\'' "$password"\nunset password\n'
                } > "$askpass_helper" || exit 1
                chmod 700 "$askpass_helper" || exit 1
                (
                    trap - EXIT HUP INT TERM
                    while IFS= read -r request < "$askpass_request"; do
                        printf '%s\n' "$_pass" > "$askpass_fifo" || exit 0
                    done
                ) &
                feeder_pid=$!
                unset _pass
                # An explicit conditional permits cleanup even under set -e.
                if SUDO_ASKPASS="$askpass_helper" "$@"; then
                    command_status=0
                else
                    command_status=$?
                fi
                exit "$command_status"
            )
            return $?
            ;;

        *)
            printf 'askpass: unknown mode: %s\n' "$mode" >&2
            return 2
            ;;
    esac
}


# Privileged command wrapper. Library helpers should use sudo_ instead of calling
# askpass directly: authentication is validated immediately before escalation.
sudo_() {
    local sudo_cmd
    askpass sudo || return $?
    sudo_cmd=$(_sudo_command_path) || return $?
    # Package scriptlets and status dialogs run GLib/libdbus clients that reach
    # for the session bus; sudo's env_reset makes them autolaunch dbus-launch,
    # which is missing on stock GNOME installs and fails elsewhere. Forward the
    # desktop session bus when the script has one.
    #
    # flatpak's CLI also warns when its export directories are missing from
    # XDG_DATA_DIRS; sudo's env_reset strips them, so every elevated flatpak
    # call printed a false "not in the search path" warning even on correctly
    # configured sessions. Rebuild the value for the elevated context instead
    # of forwarding user data paths (root's home differs from the caller's).
    local elevated_dirs="${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
    local flatpak_export_dir
    for flatpak_export_dir in \
        /var/lib/flatpak/exports/share \
        /root/.local/share/flatpak/exports/share
    do
        case ":$elevated_dirs:" in
            *:"$flatpak_export_dir":*) ;;
            *) elevated_dirs="$elevated_dirs:$flatpak_export_dir" ;;
        esac
    done

    if [[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
        "$sudo_cmd" env DBUS_SESSION_BUS_ADDRESS="$DBUS_SESSION_BUS_ADDRESS" \
            XDG_DATA_DIRS="$elevated_dirs" "$@"
    else
        "$sudo_cmd" env XDG_DATA_DIRS="$elevated_dirs" "$@"
    fi
}

# Convert escape sequences callers embed in message text (e.g. "\n") into
# real characters. Zenity and plain echo do not interpret these escapes, so
# without this the sequences would be shown literally to the user.
_msg_unescape() {
    printf '%b' "${1-}"
}

# --- MCP agent dialog passthrough ------------------------------------------
# The MCP agent server sets these for script runs it drives, so dialogs can
# never block a run nobody may be clicking and the agent relays warnings:
#   LT_AGENT_MODE=1        the run is agent-managed (never set by GUI/CLI)
#   LT_AGENT_EVENTS=path   dialog events append here: "kind\ttext" lines,
#                          kind = warn | error | prompt; the service parses
#                          them into get_job payload for the agent
#   LT_AGENT_ANSWERS=path  optional "key\tanswer" line file prepared by the
#                          service: one entry per pre-asked question, with
#                          yes/no ("yes"/"no"), one radio option, or a list
#                          selection whose lines are joined with \x1f
# Event capture keys and answer lookup both pass through _lt_agent_clean, so
# both ends see the same bytes. Outside the agent none of these are set and
# every dialog behaves exactly as before.
_lt_agent_active() {
    [[ -n "$LT_AGENT_MODE" ]]
}

_lt_agent_clean() {
    local _s="${1-}"
    _s="${_s//$'\t'/ }"
    _s="${_s//$'\r'/ }"
    _s="${_s//$'\n'/ }"
    _s="${_s//$'\x1f'/ }"
    printf '%s' "$_s"
}

_lt_agent_event() {
    [ -n "$LT_AGENT_EVENTS" ] || return 0
    printf '%s\t%s\n' "$1" "$(_lt_agent_clean "$2")" >> "$LT_AGENT_EVENTS" 2>/dev/null || true
}

# Prepared-answer lookup for one prompt (fields: kind, then every prompt
# field as the service recorded it). Echoes the answer when found; the
# newest matching entry wins when a file repeats a key.
_lt_agent_lookup() {
    [ -n "$LT_AGENT_ANSWERS" ] && [ -f "$LT_AGENT_ANSWERS" ] || return 1
    local key line found=0 answer part sep=$'\x1f'
    key="$(_lt_agent_clean "$1")"
    shift
    for part in "$@"; do
        key="${key}${sep}$(_lt_agent_clean "$part")"
    done
    while IFS= read -r line || [ -n "$line" ]; do
        part="${line#"$key"}"
        if [[ "$part" != "$line" && "${part:0:1}" == $'\t' ]]; then
            answer="${part:1}"
            found=1
        fi
    done < "$LT_AGENT_ANSWERS"
    [ "$found" = 1 ] || return 1
    printf '%s\n' "$answer"
    return 0
}

# Unified message handler
_msg() {
    local type="$1"
    local text
    text="$(_msg_unescape "$2")"
    local title="${3:-LinuxToys}"

    if [[ "$DISABLE_ZENITY" == "1" ]]; then
        return 0
    fi

    if _lt_agent_active; then
        # Informational dialogs are omitted in agent runs: the text stays in
        # the job log for the agent instead. warn()/error()/die() intercept
        # _msg in agent mode themselves, so only info reaches here.
        echo "$text"
        return 0
    fi

    case "$type" in
        # Echo before the dialog so the terminal buffer always holds the
        # message for bug reporting; the dialog is purely the visible surface.
        info)
            echo "$text"
            _zenity_run --info --text "$text" --width 360 --height 300 || true
            ;;
        warning)
            echo "$text"
            _zenity_run --warning --text "$text" --width 360 --height 300 || true
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
    local text
    text="$(_msg_unescape "$2")"
    local width="${3:-360}"
    local height="${4:-300}"
    local _reply

    if _lt_agent_active; then
        # Preset answers replace the dialog: the service validated the user's
        # choice ("yes"/"no") when queueing this run. Without one, log a
        # prompt event and show the dialog live (pass-up for prompts the
        # agent could not pre-ask); the agent tells the user about it.
        if _reply=$(_lt_agent_lookup question "$title" "$text"); then
            { [ "$_reply" = "yes" ] && return 0; } || return 1
        fi
        _lt_agent_event prompt "question: $title ($text)"
    fi

    if _zenity_can_run; then
        _zenity_run --question --title "$title" --text "$text" \
            --width "$width" --height "$height"
        return $?
    fi

    read -r -p "$text [y/N] " _reply || return 1
    [[ "$_reply" =~ ^[Yy]$ ]]
}

# Prints terminal prompts for the selectors: on the terminal stdin is attached
# to when there is one (so callers that silence stderr still show the menu),
# otherwise on stderr. Arguments are printf arguments.
_cli_out() {
    if [[ -t 0 ]] && { : >/dev/fd/0; } 2>/dev/null; then
        printf "$@" >/dev/fd/0
    else
        printf "$@" >&2
    fi
}

# Terminal selection behind radioselect/listselect when no dialog can be shown
# (CLI, TUI). Shows the title, the question and the numbered options, then
# reads the choice from stdin. Radio prints the chosen label; list prints one
# label per line. Returns 1 when nothing is chosen, which is the cancel status
# of the dialogs. Agent runs never prompt: their answers come from the
# prepared-answers file.
_cli_select() {
    local mode="$1" title="$2" text="$3" preselect="$4"
    shift 4
    local -a options=("$@") defaults=() toks=() picks=()
    local -A seen=()
    local reply tok index

    (( ${#options[@]} > 0 )) || return 1
    if _lt_agent_active; then
        return 1
    fi

    if [[ -n "$title" ]]; then
        _cli_out '\n%s\n' "$title"
    fi
    if [[ -n "$text" ]]; then
        _cli_out '%s\n' "$text"
    fi
    for index in "${!options[@]}"; do
        _cli_out '  %d) %s\n' "$((index + 1))" "${options[index]}"
    done

    if [[ "$mode" == radio ]]; then
        if [[ "$preselect" == none ]]; then
            _cli_out 'Selection: '
        else
            _cli_out 'Selection [1]: '
        fi
        read -r reply || return 1
        reply="${reply//[[:space:]]/}"
        if [[ "$preselect" != none ]]; then
            reply="${reply:-1}"
        fi
        [[ "$reply" =~ ^[0-9]+$ ]] || return 1
        reply=$(( 10#$reply ))
        (( reply >= 1 && reply <= ${#options[@]} )) || return 1
        printf '%s\n' "${options[reply - 1]}"
        return 0
    fi

    if [[ "$preselect" == all ]]; then
        for (( index = 1; index <= ${#options[@]}; index++ )); do
            defaults+=("$index")
        done
        _cli_out 'Selections (space or comma separated; Enter keeps all): '
    else
        _cli_out 'Selections (space or comma separated): '
    fi
    read -r reply || return 1
    if [[ -z "${reply//[[:space:]]/}" ]]; then
        reply="${defaults[*]-}"
    fi
    reply="${reply//,/ }"
    read -r -a toks <<< "$reply"
    (( ${#toks[@]} > 0 )) || return 1
    for tok in "${toks[@]}"; do
        [[ "$tok" =~ ^[0-9]+$ ]] || return 1
        tok=$(( 10#$tok ))
        (( tok >= 1 && tok <= ${#options[@]} )) || return 1
        if [[ -z "${seen[$tok]-}" ]]; then
            seen[$tok]=1
            picks+=("${options[tok - 1]}")
        fi
    done
    printf '%s\n' "${picks[@]}"
    return 0
}

# radioselect [--title TITLE] [--text TEXT] [--no-default] [--] OPTION...
# The first option starts selected unless --no-default is given: then nothing
# is selected and Enter cancels.
radioselect() {
    local title="LinuxToys" text="" nodefault=""
    while (( $# > 0 )); do
        case "$1" in
            --title)
                (( $# >= 2 )) || return 1
                title="$2"
                shift 2
                ;;
            --text)
                (( $# >= 2 )) || return 1
                text="$(_msg_unescape "$2")"
                shift 2
                ;;
            --no-default)
                nodefault=1
                shift
                ;;
            --)
                shift
                break
                ;;
            *)
                break
                ;;
        esac
    done
    (( $# > 0 )) || return 1

    if _lt_agent_active; then
        local _pref
        if _pref=$(_lt_agent_lookup radio "$@"); then
            printf '%s\n' "$_pref"
            return 0
        fi
        _lt_agent_event prompt "radio-select: $*"
    fi

    if _zenity_can_run; then
        local -a rows=() text_args=()
        local option state="TRUE"
        if [[ -n "$nodefault" ]]; then
            state="FALSE"
        fi
        for option in "$@"; do
            rows+=("$state" "$option")
            state="FALSE"
        done
        if [[ -n "$text" ]]; then
            text_args=(--text="$text")
        fi
        _zenity_run --list --radiolist --title="$title" "${text_args[@]}" \
            --column="" --column="Option" "${rows[@]}"
        return $?
    fi

    _cli_select radio "$title" "$text" "${nodefault:+none}" "$@"
}

# listselect [--title TITLE] [--text TEXT] [--all] [--] OPTION...
# --all starts with every option checked; Enter keeps those on the terminal.
listselect() {
    local title="LinuxToys" text="" preselect=""
    while (( $# > 0 )); do
        case "$1" in
            --title)
                (( $# >= 2 )) || return 1
                title="$2"
                shift 2
                ;;
            --text)
                (( $# >= 2 )) || return 1
                text="$(_msg_unescape "$2")"
                shift 2
                ;;
            --all)
                preselect=all
                shift
                ;;
            --)
                shift
                break
                ;;
            *)
                break
                ;;
        esac
    done
    (( $# > 0 )) || return 1

    if _lt_agent_active; then
        local _pref _sep=$'\x1f' _nl=$'\n'
        if _pref=$(_lt_agent_lookup list "$@"); then
            # Selections reach the answers file joined on \x1f (line file
            # format); re-emit one per line, exactly like zenity's output.
            printf '%s\n' "${_pref//$_sep/$_nl}"
            return 0
        fi
        _lt_agent_event prompt "multi-select: $*"
    fi

    if _zenity_can_run; then
        local -a rows=() text_args=()
        local option state="FALSE"
        if [[ "$preselect" == all ]]; then
            state="TRUE"
        fi
        for option in "$@"; do
            rows+=("$state" "$option")
        done
        if [[ -n "$text" ]]; then
            text_args=(--text="$text")
        fi
        _zenity_run --list --checklist --title="$title" "${text_args[@]}" \
            --column="" --column="Option" --separator=$'\n' "${rows[@]}"
        return $?
    fi

    _cli_select list "$title" "$text" "$preselect" "$@"
}

info() {
    { { [ -n "$CALLED_SCRIPT" ] && { [ "$1" = "$finishmsg" ] || [ "$1" = "$rebootmsg" ]; }; } && return 0; } || true
    if [ -n "$CHECKLIST_RUN" ]; then
        _msg_unescape "$1"; echo
    else
        _msg info "$1";
    fi
}
warn() {
    if _lt_agent_active; then
        # Structured event first, then the echoed text the job log already
        # captures. No popup: the agent relays the warning to the user, and
        # an unattended dialog would block the run forever.
        _lt_agent_event warn "$1"
        if [ -n "$CHECKLIST_RUN" ]; then
            echo -n "WARN: "
        fi
        _msg_unescape "$1"; echo
        return 0
    fi
    # Mirror info(): _msg prints the text itself before showing the dialog,
    # so echoing here too would duplicate the line (as zeny dialogs showed,
    # the message reached the terminal buffer twice for one call).
    if [ -n "$CHECKLIST_RUN" ]; then
        echo -n "WARN: "; _msg_unescape "$1"; echo
        return 0
    fi
    if _zenity_can_run; then
        _msg warning "$1"
    else
        _msg_unescape "$1"; echo
    fi
}
error() {
    if _lt_agent_active; then
        # nonfatal semantics: the run continues, but the service records the
        # message in the same warning channel as warn()/zenwrn().
        _lt_agent_event warn "$1"
        _msg_unescape "$1"; echo
        return 1
    fi
    _zenity_can_run || { _msg_unescape "$1"; echo; return 1; }
    _msg error "$1" "Error"
    return 1
}
die() {
    if _lt_agent_active; then
        # fatal(): the run ends here. The structured event carries the
        # message the agent must report, and the echoed line lands in the
        # job log; no popup blocks anything at this point.
        _lt_agent_event error "$1"
        _msg_unescape "$1"; echo
        exit 1
    fi
    _zenity_can_run || { _msg_unescape "$1"; echo; exit 1; }
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

# runner navigation lock control
# The terminal runner exports LINUXTOYS_RUNNER_STATE when it can honor locks.
# Locks are reference-counted so nested package helpers cannot unlock each other.
# The first lock of a run also lazily performs the CachyOS mirror preflight:
# only runs that actually enter a native package transaction pay for it. Raw
# manager calls bypass the helpers entirely, and the launcher arms the
# preflight for those scripts through the preamble instead.
runner_lock() {
    local reason="${1:-operation}"
    # ${2-default} (no colon): an explicitly empty message suppresses the echo.
    local message="${2-Starting package transaction...}"

    # Every native transaction passes through here before touching the package
    # manager, so this is the single lazy preflight point. Removals need no
    # repository access and must survive offline; the preflight itself takes
    # this lock recursively. LINUXTOYS_REQUIRE_CACHYOS_MIRRORS=0 marks
    # Flatpak/Snap entries that may continue without a completed ranking.
    if [[ "$reason" != "CachyOS mirror refresh" && "$reason" != *removal*
          && -z "${LINUXTOYS_MIRROR_PREFLIGHT_DONE:-}" ]]; then
        LINUXTOYS_MIRROR_PREFLIGHT_DONE=1
        _linuxtoys_prepare_session
        local _prep_status=$?
        if (( _prep_status != 0 )); then
            if [[ ${LINUXTOYS_REQUIRE_CACHYOS_MIRRORS:-1} != 0 ]]; then
                exit "$_prep_status"
            fi
            echo "Continuing without CachyOS mirror refresh."
        fi
    fi

    [[ -n "${LINUXTOYS_RUNNER_STATE:-}" ]] || return 0

    LINUXTOYS_RUNNER_LOCK_DEPTH=$(( ${LINUXTOYS_RUNNER_LOCK_DEPTH:-0} + 1 ))
    export LINUXTOYS_RUNNER_LOCK_DEPTH

    if (( LINUXTOYS_RUNNER_LOCK_DEPTH == 1 )); then
        printf '%s\n' "$reason" > "$LINUXTOYS_RUNNER_STATE" 2>/dev/null || true
        if [[ -n "$message" ]]; then
            echo "$message"
        fi
    fi
}

runner_unlock() {
    [[ -n "${LINUXTOYS_RUNNER_STATE:-}" ]] || return 0

    local depth=${LINUXTOYS_RUNNER_LOCK_DEPTH:-0}
    (( depth > 0 )) || return 0
    depth=$(( depth - 1 ))
    LINUXTOYS_RUNNER_LOCK_DEPTH=$depth
    export LINUXTOYS_RUNNER_LOCK_DEPTH

    if (( depth == 0 )); then
        : > "$LINUXTOYS_RUNNER_STATE" 2>/dev/null || true
    fi
}

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

# Expose pkg_fromrelease-managed repository applications from the Action Registry.
git_app_versions() {
    local exports
    exports=$(python3 "$SCRIPT_DIR/app/registry_utils.py" --export-git-releases) || {
        GIT_APPS=()
        return 1
    }
    eval "$exports"
}

# Expose AppImage release applications tracked from the Action Registry. Mirrors
# git_app_versions: APPIMAGE_APPS holds tracked app ids, and each app exposes
# APPIMAGE_<SAFE_ID>_VERSION / APPIMAGE_<SAFE_ID>_REPO where SAFE_ID is the app
# id with non-identifier characters folded to underscores.
appimage_app_versions() {
    local exports
    exports=$(python3 "$SCRIPT_DIR/app/registry_utils.py" --export-appimage-releases) || {
        APPIMAGE_APPS=()
        return 1
    }
    eval "$exports"
}

# Flatpak component IDs are reverse-DNS names: at least three dot-separated
# labels (e.g. it.mijorus.gearlever, org.gnome.Calculator). Native AppStream
# IDs usually carry a .desktop suffix, and display names passed to
# call_script contain spaces or slashes. Only a Flatpak ID pattern can justify
# bootstrapping Flatpak support during AppStream resolution.
_appstream_target_is_flatpak_id () {
    local id="$1"
    [[ -z "$id" ]] && return 1
    [[ "$id" == *.desktop || "$id" == *.Desktop ]] && return 1
    [[ "$id" == *" "* || "$id" == */* ]] && return 1
    [[ "$id" =~ ^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+){2,}$ ]]
}

# script calling -- used for scripts to call other scripts from the app.
call_script () {
    local script_name="$1"
    [[ -z "$script_name" ]] && die "call_script: script name not provided"
    [[ -z "$CACHE_DIR" ]] && die "call_script: CACHE_DIR environment variable not set"

    script_name="${script_name%.sh}"
    local script_file="${script_name}.sh"
    local found_script=""
    local script_display_name=""
    local script_registry_name=""
    local script_registry_disabled=""
    local repo_app_id=""
    local repo_url=""

    found_script=$(find "$CACHE_DIR" -maxdepth 3 -type f \
        -name "$script_file" 2>/dev/null | head -n1)

    if [[ -n "$found_script" && -f "$found_script" ]]; then
        python3 "$SCRIPT_DIR/app/compat.py" --check-script "$found_script" || {
            echo "'$script_name' is not compatible with this host, skipping. This is not an error."
            return 2
        }

        script_display_name=$(
            sed -n 's/^# name:[[:space:]]*//p' "$found_script" |
            head -n1
        )
        [[ -n "$script_display_name" ]] || script_display_name="$script_name"

        script_registry_disabled=$(
            sed -n 's/^# registry:[[:space:]]*//p' "$found_script" |
            head -n1 |
            tr '[:upper:]' '[:lower:]'
        )

        # Preserve pretty names for ordinary scripts, but use the internal file ID
        # when the # name header is a localization key.
        if python3 - "$script_display_name" <<'PY' >/dev/null 2>&1
import os
import sys
sys.path.insert(0, os.environ["SCRIPT_DIR"])
from app.lang_utils import load_translations
key = sys.argv[1]
translations = load_translations()
sys.exit(0 if translations.get(key, key) != key else 1)
PY
        then
            script_registry_name="$script_name"
        else
            script_registry_name="$script_display_name"
        fi
    else
        # Physical script not found: resolve a compatible repository-list entry
        # through its normalized repo_app_id (e.g. PRISM_LAUNCHER).
        # Command substitution (not mapfile over process substitution) so the
        # resolver's exit status is actually captured: PIPESTATUS cannot see a
        # process substitution, and the resolver reports a distinct status for
        # "declared but not installable on this host".
        local -a repo_selection=()
        local repo_output
        repo_output=$(python3 "$SCRIPT_DIR/app/library_loader.py" --materialize-repo "$script_name")
        local resolve_status=$?
        [[ -n "$repo_output" ]] && mapfile -t repo_selection <<< "$repo_output"

        if [[ $resolve_status -eq 4 ]]; then
            # The repository listing declares this app, but not for this host.
            # Skip exactly like an incompatible physical script instead of
            # reporting "not found" (or consulting the AppStream resolver).
            echo "'$script_name' is not compatible with this host, skipping. This is not an error."
            return 2
        fi

        if [[ $resolve_status -eq 0 && ${#repo_selection[@]} -eq 3 ]]; then
            found_script="${repo_selection[0]}"
            script_display_name="${repo_selection[1]}"
            repo_url="${repo_selection[2]}"
            repo_app_id="${script_name^^}"
            script_registry_name="$script_display_name"
        else
            # Repository-list resolution failed. AppStream is the final resolver;
            # it accepts a stable component ID or an exact display/canonical name.
            local -a appstream_selection=()
            local appstream_output
            appstream_output=$(python3 "$SCRIPT_DIR/app/library_loader.py" --materialize-appstream "$script_name")
            local appstream_status=$?
            [[ -n "$appstream_output" ]] && mapfile -t appstream_selection <<< "$appstream_output"

            if [[ $appstream_status -ne 0 || ${#appstream_selection[@]} -ne 4 ]]; then
                # Flatpak-backed AppStream IDs cannot resolve while Flatpak or
                # its Flathub remote is unavailable: the catalog has no Flathub
                # component to index. Bootstrap Flathub support once (the same
                # preparation pkg_flat performs) and retry. The Python resolver
                # refreshes the AppStream catalog after the source universe
                # changed, including Flathub's local AppStream database.
                # Flatpak is systemd-only, so the bootstrap runs only when the
                # target itself looks like a Flatpak component ID; native and
                # other sources never trigger a Flatpak installation.
                if _appstream_target_is_flatpak_id "$script_name" &&
                   { ! command -v flatpak &>/dev/null ||
                     ! flatpak remote-list 2>/dev/null | grep -q flathub; }; then
                    call_script flathub || die "call_script: Failed to prepare Flathub support for '$script_name'"
                    appstream_output=$(python3 "$SCRIPT_DIR/app/library_loader.py" --materialize-appstream "$script_name")
                    appstream_status=$?
                    appstream_selection=()
                    [[ -n "$appstream_output" ]] && mapfile -t appstream_selection <<< "$appstream_output"
                fi
            fi

            if [[ $appstream_status -ne 0 || ${#appstream_selection[@]} -ne 4 ]]; then
                die "call_script: Script, repository app or AppStream app '$script_name' not found"
            fi

            found_script="${appstream_selection[0]}"
            script_display_name="${appstream_selection[1]}"
            script_registry_name="$script_display_name"
        fi
    fi

    [[ -n "$script_registry_name" ]] || script_registry_name="$script_display_name"

    shift

    # Keep track of the caller's transaction.
    local parent_transmap="$TRANSMAP_PATH"

    # Create an independent transaction for the called script.
    local child_transmap
    child_transmap=$(mktemp "/tmp/linuxtoys-called-XXXXXX.transmap") ||
        die "call_script: Failed to create child transmap"

    (
        export CALLED_SCRIPT=1
        export TRANSMAP_PATH="$child_transmap"
        if [[ -n "$repo_app_id" ]]; then
            export LINUXTOYS_REPO_APP_ID="$repo_app_id"
            export LINUXTOYS_REPO_URL="$repo_url"
        fi

        python3 "$SCRIPT_DIR/app/library_loader.py" "$found_script" "$@"
    )
    local status=$?

    if [[ $status -eq 0 ]]; then
        # Commit the called script's transaction independently, unless the
        # script opted out of registry tracking via `# registry: no`.
        if [[ -s "$child_transmap" ]]; then
            if [[ "$script_registry_disabled" != "no" ]]; then
                python3 "$SCRIPT_DIR/app/term_registry.py" \
                    save "$script_registry_name" "$child_transmap" ||
                    die "Failed to save transaction for $script_display_name"
            fi
            _append_transmap "called $script_registry_name"
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
       [ -f "$CACHE_DIR/lists/$hook" ]; then
        path="$CACHE_DIR/lists/$hook"
    elif [ -f "$SCRIPT_DIR/scripts/lists/$hook" ]; then
        path="$SCRIPT_DIR/scripts/lists/$hook"
    else
        die "Repository hook script not found: $hook"
    fi

    source "$path"
}

# Run before user-triggered script code, through the canonical script preamble.
# A private directory is shared by all runners in this application session.
_linuxtoys_prepare_session() (
    [[ -r /etc/os-release ]] || return 0
    source /etc/os-release
    [[ ${ID:-} == cachyos ]] || return 0
    [[ -n ${LINUXTOYS_EXECUTION_SESSION_DIR:-} ]] || return 0

    local session_dir="$LINUXTOYS_EXECUTION_SESSION_DIR"
    local mirror_status=1
    # Hold the lock until ranking finishes, so parallel runners wait for the
    # first result rather than starting installations with an unfinished list.
    exec 9>"$session_dir/cachyos-mirrors.lock" || return 1
    flock -x 9 || return 1
    # Only a completed successful refresh is cached. A failed attempt remains
    # retryable on the next operation, without restarting LinuxToys.
    if [[ -f "$session_dir/cachyos-mirrors.status" ]] &&
       [[ $(cat "$session_dir/cachyos-mirrors.status" 2>/dev/null) == 0 ]]; then
        return 0
    fi

    echo "Rating CachyOS mirrors. Please wait..."
    # The rating itself already reports on the terminal; suppress the generic
    # transaction message so a mirror refresh is never announced as one.
    runner_lock "CachyOS mirror refresh" ""
    # cachyos-rate-mirrors and pacman are chatty; keep their output out of the
    # terminal viewer unless the operation fails (then show it for diagnosis).
    local rating_log
    rating_log=$(mktemp "$session_dir/cachyos-rating.XXXXXX") || rating_log=/dev/null
    if { sudo_ cachyos-rate-mirrors && sudo_ pacman -Sy --noconfirm; } >"$rating_log" 2>&1; then
        # Cache success only after both mirror rating and database refresh.
        [[ "$rating_log" == /dev/null ]] || rm -f -- "$rating_log"
        printf '0\n' > "$session_dir/cachyos-mirrors.status"
        mirror_status=0
    else
        mirror_status=$?
        rm -f -- "$session_dir/cachyos-mirrors.status"
        printf 'CachyOS mirror rating or package database synchronization failed (status %d). Output follows:\n' "$mirror_status" >&2
        cat "$rating_log" >&2
        [[ "$rating_log" == /dev/null ]] || rm -f -- "$rating_log"
    fi
    runner_unlock
    return "$mirror_status"
)

# --- Once-per-boot silent clock enforcement ---
# This file is sourced by every launch path (GUI, CLI, checklist batches,
# revert dialogs, root services), which is exactly "app launch" from the
# shell layer; the boot-scoped stamp makes all but the first run of a boot
# no-ops. Skewed clocks would fail Debian 13+/Ubuntu 25.10+ sqv signature
# verification ('Not live until') downstream. Corrections prefer the system's
# NTP service and fall back to an HTTP Date step; runs that would need a
# privilege prompt are stamped "pending" and finished right after the first
# successful authorization through askpass's timefix_afterauth hook.
timefix_bootguard || true
