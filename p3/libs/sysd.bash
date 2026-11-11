
# Reload the systemd manager once per script run (shared latch preamble of
# sysd_enable/sysd_start and their --user variants).
_sysd_reload_once() {
    [ -n "${daemon_reloaded:-}" ] && return 0
    sudo_ systemctl daemon-reload || fatal "Failed to reload systemd daemon"
    daemon_reloaded="1"
}

sysd_enable() {
    _sysd_reload_once
    for svc in "$@"; do
        sudo_ systemctl enable "$svc" || fatal "Failed to enable service $svc"
        _append_transmap "sysd enabled $svc"
    done
}
sysd_disable() {
    for svc in "$@"; do
        sudo_ systemctl disable "$svc" || fatal "Failed to disable service $svc"
        _append_transmap "sysd disabled $svc"
    done
}
sysd_start() {
    _sysd_reload_once
    for svc in "$@"; do
        sudo_ systemctl start "$svc" || fatal "Failed to start service $svc"
        _append_transmap "sysd started $svc"
    done
}
sysd_stop() {
    for svc in "$@"; do
        sudo_ systemctl stop "$svc" || fatal "Failed to stop service $svc"
        _append_transmap "sysd stopped $svc"
    done
}

sysd_enable_usr() {
    _sysd_reload_once
    for svc in "$@"; do
        systemctl --user enable "$svc" || fatal "Failed to enable service $svc"
        _append_transmap "sysd usermode enabled $svc"
    done
}
sysd_disable_usr() {
    for svc in "$@"; do
        systemctl --user disable "$svc" || fatal "Failed to disable service $svc"
        _append_transmap "sysd usermode disabled $svc"
    done
}
sysd_start_usr() {
    _sysd_reload_once
    for svc in "$@"; do
        systemctl --user start "$svc" || fatal "Failed to start service $svc"
        _append_transmap "sysd usermode started $svc"
    done
}
sysd_stop_usr() {
    for svc in "$@"; do
        systemctl --user stop "$svc" || fatal "Failed to stop service $svc"
        _append_transmap "sysd usermode stopped $svc"
    done
}
