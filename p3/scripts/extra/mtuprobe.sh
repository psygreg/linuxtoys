#!/usr/bin/env bash
# name: mtuprobe
# description: mtuprobe_desc
# icon: bbr.svg
# compat: !steamos, !ostree, !cachy
# nocontainer
# systemd: yes

askpass
prep_create /usr/lib/sysctl.d/99-mtuprobe.conf

cat <<'EOF' | sudo_ tee /usr/lib/sysctl.d/99-mtuprobe.conf >/dev/null
net.ipv4.tcp_mtu_probing = 1
net.ipv4.tcp_base_mss = 1024
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

_sysctl_run sysctl -p /usr/lib/sysctl.d/99-mtuprobe.conf || die "Failed to enable MTU probing"
_sysctl_run sysctl --system || die "Failed to refresh sysctl"

info "$finishmsg"
