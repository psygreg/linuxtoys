# --- SystemD Operations ---

sysd_enable() {
    if [ ! -n "$daemon_reloaded" ]; then
        sudo systemctl daemon-reload || fatal "Failed to reload systemd daemon"
        daemon_reloaded="1"
    fi
    for svc in "$@"; do
        sudo systemctl enable "$svc" || fatal "Failed to enable service $svc"
        _append_transmap "sysd enabled $svc"
    done
}
sysd_disable() {
    for svc in "$@"; do
        sudo systemctl disable "$svc" || fatal "Failed to disable service $svc"
        _append_transmap "sysd disabled $svc"
    done
}
sysd_start() {
    if [ ! -n "$daemon_reloaded" ]; then
        sudo systemctl daemon-reload || fatal "Failed to reload systemd daemon"
        daemon_reloaded="1"
    fi
    for svc in "$@"; do
        sudo systemctl start "$svc" || fatal "Failed to start service $svc"
        _append_transmap "sysd started $svc"
    done
}
sysd_stop() {
    for svc in "$@"; do
        sudo systemctl stop "$svc" || fatal "Failed to stop service $svc"
        _append_transmap "sysd stopped $svc"
    done
}

sysd_enable_usr() {
    if [ ! -n "$daemon_reloaded" ]; then
        sudo systemctl daemon-reload || fatal "Failed to reload systemd daemon"
        daemon_reloaded="1"
    fi
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
    if [ ! -n "$daemon_reloaded" ]; then
        sudo systemctl daemon-reload || fatal "Failed to reload systemd daemon"
        daemon_reloaded="1"
    fi
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
