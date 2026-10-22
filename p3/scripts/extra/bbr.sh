#!/bin/bash
# name: TCP BBR3
# description: bbr_desc
# icon: bbr.svg
# compat: !steamos, !ostree, !cachy
# nocontainer
# systemd: yes

if ! grep -qw bbr /proc/sys/net/ipv4/tcp_available_congestion_control; then
    if ! { sudo_ modinfo tcp_bbr &>/dev/null && sudo_ modprobe tcp_bbr; }; then
        if [ -z "$CALLED_SCRIPT" ]; then
            warn "TCP BBR is not available on this kernel."
        else
            echo "TCP BBR is not available on this kernel."
        fi
        exit 100
    else
        prep_edit /etc/modules-load.d/modules.conf
        echo 'tcp_bbr' | sudo_ tee -a /etc/modules-load.d/modules.conf
    fi
fi

prep_create /usr/lib/sysctl.d/99-bbr.conf
cat <<'EOF' | sudo_ tee /usr/lib/sysctl.d/99-bbr.conf >/dev/null
# BBR v3 Congestion Control Configuration
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# TCP Buffer Optimization
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728

# TCP Performance Tuning
net.ipv4.tcp_window_scaling = 1
net.ipv4.tcp_timestamps = 1
net.ipv4.tcp_sack = 1
net.ipv4.tcp_no_metrics_save = 1
net.ipv4.tcp_moderate_rcvbuf = 1

# Network Stack Optimization
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_slow_start_after_idle = 0
EOF

# sysctl echoes every key it writes (-p) and every sysctl.d file it re-applies
# (--system). Capture that chatter so a normal run stays quiet, but replay it
# verbatim when the command actually fails so real errors are not swallowed.
_sysctl_run () {
    local _out _status
    _out=$(mktemp) || return 1
    sudo_ "$@" >"$_out" 2>&1
    _status=$?
    if [ "$_status" -ne 0 ]; then
        cat "$_out" >&2
    fi
    rm -f "$_out"
    return "$_status"
}

_sysctl_run sysctl -p /usr/lib/sysctl.d/99-bbr.conf || die "Failed to enable tcp_bbr settings"
_sysctl_run sysctl --system || die "Failed to refresh sysctl"

info "$finishmsg"
